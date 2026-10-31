import unittest
from unittest.mock import Mock, patch

from tusker_ai.model_store import _PinnedHTTPSConnection, _resolve_public_address


class PinnedDownloadNetworkTests(unittest.TestCase):
    def test_dns_resolution_rejects_mixed_public_and_private_answers(self):
        public = (2, 1, 6, "", ("8.8.8.8", 443))
        private = (2, 1, 6, "", ("127.0.0.1", 443))
        with patch("tusker_ai.model_store.socket.getaddrinfo", return_value=[public, private]):
            with self.assertRaises(ValueError):
                _resolve_public_address("models.example.test", 443)

    def test_connection_uses_pinned_ip_but_preserves_tls_hostname(self):
        answer = (2, 1, 6, "", ("8.8.8.8", 443))
        raw_socket = object()
        wrapped_socket = object()
        context = Mock()
        context.wrap_socket.return_value = wrapped_socket
        with patch("tusker_ai.model_store.socket.getaddrinfo", return_value=[answer]), patch(
            "tusker_ai.model_store.socket.create_connection", return_value=raw_socket
        ) as connect:
            connection = _PinnedHTTPSConnection("models.example.test:443", context=context, timeout=3)
            connection.connect()
        connect.assert_called_once_with(("8.8.8.8", 443), 3, None)
        context.wrap_socket.assert_called_once_with(raw_socket, server_hostname="models.example.test")
        self.assertIs(connection.sock, wrapped_socket)

    def test_literal_non_global_ip_is_rejected(self):
        with self.assertRaises(ValueError):
            _resolve_public_address("127.0.0.1", 443)


if __name__ == "__main__":
    unittest.main()
