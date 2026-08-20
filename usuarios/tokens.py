from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class ContaSetupTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "usuarios.tokens.ContaSetupTokenGenerator"

    def _timeout(self) -> int:
        return int(getattr(settings, "CONTA_SETUP_TIMEOUT", 48 * 60 * 60))

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False
        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret),
                token,
            ):
                break
        else:
            return False
        if (self._num_seconds(self._now()) - ts) > self._timeout():
            return False
        return True


conta_setup_token_generator = ContaSetupTokenGenerator()
