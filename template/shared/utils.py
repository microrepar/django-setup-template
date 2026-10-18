import ipaddress
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def validar_ip(ip):
    """
    Valida e normaliza um endereço IPv4 ou IPv6.

    Returns:
        str: o IP se válido, ou None (com log de aviso) se inválido
    """
    if not ip:
        return None

    try:
        # ipaddress.ip_address() valida tanto IPv4 quanto IPv6
        ipaddress.ip_address(ip)
        return ip
    except ValueError:
        logger.warning(f'Invalid IP address format: {ip}')
        return None


def ip_em_rede(ip, rede_cidr):
    """
    Verifica se o IP pertence à rede (CIDR) informada.

    Returns:
        bool: True se o IP estiver no CIDR; False se estiver fora,
        se o IP/CIDR for inválido ou se os protocolos divergirem
    """
    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(rede_cidr, strict=False)
    except (ValueError, TypeError):
        logger.warning(f'TRUSTED_PROXY_NET ou IP inválido: rede={rede_cidr} ip={ip}')
        return False


def get_client_ip(request):
    """
    Obtém e valida o IP do cliente — fonte única consumida por django-axes
    (AXES_CLIENT_IP_CALLABLE); qualquer outro consumidor de IP de cliente
    deve chamar esta função, não reimplantar a lógica.

    Suporta IPv4 e IPv6. Retorna None se o IP for inválido.

    Fora de proxies confiáveis (TRUST_PROXY=False), usa apenas REMOTE_ADDR:
    X-Forwarded-For é forjável pelo cliente e burla o bloqueio de força
    bruta e a auditoria de IPs (padrão portado do projeto Imprensa,
    achado A9 da auditoria de 22/09/2026).

    Atrás de proxies confiáveis (TRUST_PROXY=True), usa a entrada do
    X-Forwarded-For escrita pelo proxy mais externo da cadeia confiável,
    na posição -(1 + TRUSTED_PROXY_DEPTH): cada proxy confiável anexa o
    endereço que observou à direita, então as entradas à esquerda são
    controláveis pelo cliente e são ignoradas. Se TRUSTED_PROXY_NET estiver
    definido, o header só é considerado quando o REMOTE_ADDR (proxy
    imediato) pertencer ao CIDR informado.

    Args:
        request: Objeto HttpRequest do Django

    Returns:
        str: IP validado (IPv4 ou IPv6) ou None se inválido

    Examples:
        >>> get_client_ip(request)
        '192.168.1.1'  # IPv4 válido
        '2001:db8::1'  # IPv6 válido
        None  # IP inválido ou ausente
    """
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if forwarded_for and getattr(settings, 'TRUST_PROXY', False):
        proxy_imediato = request.META.get('REMOTE_ADDR', '').strip()
        rede = getattr(settings, 'TRUSTED_PROXY_NET', '')

        if not rede or ip_em_rede(proxy_imediato, rede):
            entradas = [e.strip() for e in forwarded_for.split(',') if e.strip()]
            indice = len(entradas) - 1 - getattr(settings, 'TRUSTED_PROXY_DEPTH', 0)

            if 0 <= indice < len(entradas):
                ip = validar_ip(entradas[indice])
                if ip:
                    return ip

    # Fallback seguro em todos os outros casos: REMOTE_ADDR da conexão
    ip = request.META.get('REMOTE_ADDR', '').strip()
    return validar_ip(ip)
