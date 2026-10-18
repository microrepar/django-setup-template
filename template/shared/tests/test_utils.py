from django.conf import settings
from django.test import RequestFactory, TestCase, override_settings
from django.utils.module_loading import import_string

from shared.utils import get_client_ip


class TestGetClientIp(TestCase):
    """O IP de cliente tem uma fonte única (get_client_ip) porque a primeira
    entrada do X-Forwarded-For é forjável pelo cliente mesmo atrás do nginx
    ($proxy_add_x_forwarded_for preserva o header recebido). Com o IP sob
    controle do atacante, cada tentativa de login pareceria vir de um
    cliente novo e o django-axes nunca esgotaria o bloqueio. A fonte
    confiável é a entrada escrita pelo proxy mais externo da cadeia
    (padrão portado do projeto Imprensa, achado A9)."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_fora_de_proxy_confiavel_ignora_xff(self):
        """Sem TRUST_PROXY, XFF forjado é ignorado: vale o REMOTE_ADDR"""
        request = self.factory.get(
            '/', REMOTE_ADDR='9.9.9.9', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8'
        )

        self.assertEqual(get_client_ip(request), '9.9.9.9')

    def test_sem_xff_retorna_remote_addr(self):
        request = self.factory.get('/', REMOTE_ADDR='9.9.9.9')

        self.assertEqual(get_client_ip(request), '9.9.9.9')

    @override_settings(TRUST_PROXY=True, TRUSTED_PROXY_NET='')
    def test_atras_do_proxy_usa_entrada_do_nginx(self):
        """Depth 0 (só nginx na frente): a última entrada é a que o nginx
        observou e anexou — as anteriores vieram do cliente"""
        request = self.factory.get(
            '/', REMOTE_ADDR='172.18.0.9', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8'
        )

        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(TRUST_PROXY=True, TRUSTED_PROXY_NET='', TRUSTED_PROXY_DEPTH=1)
    def test_depth_1_usa_entrada_do_proxy_externo(self):
        """Cliente → proxy externo → nginx → Django: a penúltima entrada é
        o cliente real escrito pelo proxy externo; a última é o IP que o
        nginx observou (o próprio proxy externo)"""
        request = self.factory.get(
            '/', REMOTE_ADDR='172.18.0.9',
            HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8, 203.0.113.10',
        )

        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(TRUST_PROXY=True, TRUSTED_PROXY_NET='10.0.0.0/8')
    def test_remote_addr_fora_do_cidr_descarta_xff(self):
        """XFF só é confiável vindo de proxy imediato conhecido: acesso
        direto de fora da rede informada cai para o REMOTE_ADDR"""
        request = self.factory.get(
            '/', REMOTE_ADDR='172.18.0.9', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8'
        )

        self.assertEqual(get_client_ip(request), '172.18.0.9')

    @override_settings(TRUST_PROXY=True, TRUSTED_PROXY_NET='172.16.0.0/12')
    def test_remote_addr_dentro_do_cidr_usa_xff(self):
        request = self.factory.get(
            '/', REMOTE_ADDR='172.18.0.9', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8'
        )

        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(TRUST_PROXY=True, TRUSTED_PROXY_NET='')
    def test_ip_invalido_na_posicao_confia_cai_para_remote_addr(self):
        request = self.factory.get(
            '/', REMOTE_ADDR='172.18.0.9', HTTP_X_FORWARDED_FOR='1.2.3.4, nao-e-ip'
        )

        self.assertEqual(get_client_ip(request), '172.18.0.9')

    def test_ip_invalido_em_remote_addr_retorna_none(self):
        request = self.factory.get('/', REMOTE_ADDR='nao-e-ip')

        self.assertIsNone(get_client_ip(request))

    def test_ipv6_e_aceito(self):
        request = self.factory.get('/', REMOTE_ADDR='2001:db8::1')

        self.assertEqual(get_client_ip(request), '2001:db8::1')

    def test_axes_usa_a_mesma_fonte_de_ip(self):
        """axes (e qualquer auditoria de IP) tem que bloquear/auditar o
        MESMO IP que get_client_ip resolve — fonte única, sem réplica de lógica"""
        callable_path = settings.AXES_CLIENT_IP_CALLABLE

        self.assertEqual(callable_path, 'shared.utils.get_client_ip')
        self.assertTrue(callable(import_string(callable_path)))
