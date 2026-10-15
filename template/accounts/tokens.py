from django.contrib.auth.tokens import PasswordResetTokenGenerator


class ActivationTokenGenerator(PasswordResetTokenGenerator):
    """Token de ativação de cadastro: uso único, sem last_login no hash.

    O gerador padrão (reset de senha) invalida o token a cada login —
    desejável para reset (quem logou não precisa mais do link), mas errado
    para ativação: o login não é bloqueado para e-mail não verificado, e a
    pessoa que cadastra, loga e só depois clica no link de ativação recebe
    "link inválido" sem culpa nenhuma. Senha, e-mail e o nonce entram no
    hash: troca de senha invalida o link (que pertence à conta tal como
    cadastrada), e o incremento do nonce na verificação mata o link usado —
    um link de ativação vale exatamente uma confirmação.
    """

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.password}{timestamp}{user.email}{user.activation_nonce}'


activation_token_generator = ActivationTokenGenerator()
