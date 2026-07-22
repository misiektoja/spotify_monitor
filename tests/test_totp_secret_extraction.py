from debug import spotify_monitor_totp_test as totp_test


# Verifies inline secret objects are extracted in both supported property orders
def test_extract_bundle_secrets_supports_current_object_literals():
    source = '''
    const first = {secret: "alpha", version: 61};
    const second = {"version": 62, 'secret': 'beta'};
    const duplicate = {secret: "alpha", version: 61};
    '''

    assert totp_test.extract_bundle_secrets(source) == [
        {'secret': 'alpha', 'version': 61, 'source': 'bundle'},
        {'secret': 'beta', 'version': 62, 'source': 'bundle'},
    ]


# Verifies quoted secret values use the same escape decoding as the v1.3 grabber
def test_extract_bundle_secrets_decodes_escaped_strings():
    source = r'''const item = {secret: "alpha\"beta", version: 63};'''

    assert totp_test.extract_bundle_secrets(source) == [
        {'secret': 'alpha"beta', 'version': 63, 'source': 'bundle'},
    ]


# Verifies unrelated objects are ignored by the inline secret scanner
def test_extract_bundle_secrets_ignores_nonmatching_objects():
    source = '''
    const missingVersion = {secret: "alpha"};
    const wrongType = {secret: 123, version: 64};
    const extraProperty = {secret: "beta", enabled: true, version: 65};
    '''

    assert totp_test.extract_bundle_secrets(source) == []
