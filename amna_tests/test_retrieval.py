from amna_rag.services.retrieval_service import tokenize

def test_tokenize_keeps_error_codes_and_device_terms():
    tokens = tokenize("VPN-204 on ThinkPad T14; printer error 0x0000011b")
    assert "vpn-204" in tokens
    assert "thinkpad" in tokens
    assert "0x0000011b" in tokens
