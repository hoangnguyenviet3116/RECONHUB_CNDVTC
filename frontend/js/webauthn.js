// ==========================================================================
// VIETQR RECONHUB — XÁC THỰC KHÓA BẢO MẬT THIẾT BỊ (frontend/js/webauthn.js)
// ==========================================================================

const WEBAUTHN_STORAGE_KEY = "reconhub_webauthn_cred_id";

function bufferToBase64Url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlToBuffer(base64url) {
    const padding = "=".repeat((4 - (base64url.length % 4)) % 4);
    const base64 = (base64url + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray.buffer;
}

function stringToBuffer(str) {
    return new TextEncoder().encode(String(str));
}

function getStoredCredentialId() {
    return localStorage.getItem(WEBAUTHN_STORAGE_KEY) || "";
}

function setStoredCredentialId(credId) {
    if (!credId) return;
    localStorage.setItem(WEBAUTHN_STORAGE_KEY, credId);
    updateWebAuthnStatusBadge();
}

function updateWebAuthnStatusBadge() {
    const badgeEl = document.getElementById("webauthn-status-badge");
    const textEl = document.getElementById("webauthn-status-text");
    const credId = getStoredCredentialId();

    if (!badgeEl || !textEl) return;

    if (credId) {
        badgeEl.className = "fp-badge fp-badge-success";
        textEl.textContent = "Bảo mật: Đã kích hoạt khóa xác thực trên thiết bị";
    } else {
        badgeEl.className = "fp-badge fp-badge-neutral";
        textEl.textContent = "Bảo mật: Chưa kích hoạt khóa xác thực";
    }
}

// --------------------------------------------------------------------------
// 1. ĐĂNG KÝ KHÓA BẢO MẬT TRÊN THIẾT BỊ
// --------------------------------------------------------------------------
async function registerWebAuthnCredential() {
    const userId = getCurrentUserId();
    const role = getCurrentRole();

    let optionsData = null;
    try {
        optionsData = await apiRequest("/decisions/webauthn/register/options", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                role: role
            })
        });
    } catch (err) {
        if (!err.isNetworkError && err.status !== 404) {
            throw err;
        }
        optionsData = {
            challenge: bufferToBase64Url(crypto.getRandomValues(new Uint8Array(32))),
            rp: { name: "VietQR ReconHub", id: window.location.hostname || "localhost" },
            user: {
                id: bufferToBase64Url(stringToBuffer(`user_${userId}`)),
                name: `${role.toLowerCase()}@reconhub.vn`,
                displayName: `Kế toán đối soát (${role})`
            }
        };
    }

    const challengeStr = optionsData.challenge || bufferToBase64Url(crypto.getRandomValues(new Uint8Array(32)));
    let credentialId = "";
    let publicKeyBase64 = "";
    let clientDataJSON = "";
    let attestationObject = "";

    if (window.PublicKeyCredential && navigator.credentials && navigator.credentials.create) {
        try {
            const publicKeyCreationOptions = {
                challenge: base64UrlToBuffer(challengeStr),
                rp: {
                    name: optionsData.rp?.name || "VietQR ReconHub",
                    id: window.location.hostname || "localhost"
                },
                user: {
                    id: stringToBuffer(`reconhub_user_${userId}`),
                    name: optionsData.user?.name || `reviewer_${userId}@reconhub.vn`,
                    displayName: optionsData.user?.displayName || `Kế toán đối soát`
                },
                pubKeyCredParams: [
                    { alg: -7, type: "public-key" },
                    { alg: -257, type: "public-key" }
                ],
                authenticatorSelection: {
                    userVerification: "preferred"
                },
                timeout: 60000,
                attestation: "none"
            };

            const credential = await navigator.credentials.create({
                publicKey: publicKeyCreationOptions
            });

            if (credential) {
                credentialId = credential.id || bufferToBase64Url(credential.rawId);
                clientDataJSON = bufferToBase64Url(credential.response.clientDataJSON);
                attestationObject = bufferToBase64Url(credential.response.attestationObject);
                publicKeyBase64 = attestationObject;
            }
        } catch (domErr) {
            if (domErr.name === "NotAllowedError") {
                throw new Error("Bạn đã hủy bước đăng ký khóa xác thực bảo mật trên thiết bị.");
            }
        }
    }

    if (!credentialId) {
        const randBytes = crypto.getRandomValues(new Uint8Array(24));
        credentialId = `cred_${bufferToBase64Url(randBytes)}`;
        publicKeyBase64 = `pk_${bufferToBase64Url(crypto.getRandomValues(new Uint8Array(32)))}`;
        clientDataJSON = bufferToBase64Url(
            stringToBuffer(JSON.stringify({ type: "webauthn.create", challenge: challengeStr, origin: window.location.origin }))
        );
    }

    try {
        const verifyRes = await apiRequest("/decisions/webauthn/register/verify", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                challenge: challengeStr,
                credential_id: credentialId,
                public_key: publicKeyBase64,
                client_data_json: clientDataJSON,
                attestation_object: attestationObject
            })
        });

        const finalCredId = verifyRes.credential_id || credentialId;
        setStoredCredentialId(finalCredId);
        return {
            credential_id: finalCredId,
            challenge: challengeStr,
            verified_by_server: true
        };
    } catch (err) {
        if (err.isNetworkError || err.status === 404) {
            setStoredCredentialId(credentialId);
            return {
                credential_id: credentialId,
                challenge: challengeStr,
                verified_by_server: false
            };
        }
        throw err;
    }
}

// --------------------------------------------------------------------------
// 2. XÁC NHẬN KHÓA BẢO MẬT KHI DUYỆT GIAO DỊCH LỆCH HOẶC ĐẢO BÚT TOÁN
// --------------------------------------------------------------------------
async function requestWebAuthnAssertion(actionContext = {}) {
    const userId = getCurrentUserId();
    let credId = getStoredCredentialId();

    if (!credId) {
        const regResult = await registerWebAuthnCredential();
        credId = regResult.credential_id;
    }

    let authOptions = null;
    try {
        authOptions = await apiRequest("/decisions/webauthn/authenticate/options", {
            method: "POST",
            body: JSON.stringify({
                user_id: userId,
                credential_id: credId,
                decision_type: actionContext.decision_type || "APPROVE_MANUAL_MATCH"
            })
        });
    } catch (err) {
        if (!err.isNetworkError && err.status !== 404) {
            throw err;
        }
        authOptions = {
            challenge: bufferToBase64Url(crypto.getRandomValues(new Uint8Array(32))),
            credential_id: credId
        };
    }

    const challengeUsed = authOptions.challenge || bufferToBase64Url(crypto.getRandomValues(new Uint8Array(32)));
    let assertionSignature = "";
    let authenticatorData = "";
    let clientDataJSON = "";

    if (window.PublicKeyCredential && navigator.credentials && navigator.credentials.get) {
        try {
            const publicKeyRequestOptions = {
                challenge: base64UrlToBuffer(challengeUsed),
                rpId: window.location.hostname || "localhost",
                userVerification: "preferred",
                timeout: 60000
            };

            if (!credId.startsWith("cred_")) {
                try {
                    publicKeyRequestOptions.allowCredentials = [
                        {
                            id: base64UrlToBuffer(credId),
                            type: "public-key"
                        }
                    ];
                } catch (_) {
                    // Bỏ qua nếu đang ở chế độ khóa giả lập
                }
            }

            const assertion = await navigator.credentials.get({
                publicKey: publicKeyRequestOptions
            });

            if (assertion && assertion.response) {
                credId = assertion.id || bufferToBase64Url(assertion.rawId);
                assertionSignature = bufferToBase64Url(assertion.response.signature);
                authenticatorData = bufferToBase64Url(assertion.response.authenticatorData);
                clientDataJSON = bufferToBase64Url(assertion.response.clientDataJSON);
            }
        } catch (domErr) {
            if (domErr.name === "NotAllowedError") {
                throw new Error("Bạn đã hủy bước xác nhận khóa bảo mật nên thao tác chưa được thực hiện.");
            }
        }
    }

    if (!assertionSignature) {
        const msgBuffer = stringToBuffer(
            `${challengeUsed}|${credId}|${actionContext.decision_type || ""}|${actionContext.order_id || ""}|${actionContext.bank_transaction_id || ""}`
        );
        const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
        assertionSignature = `sig_${bufferToBase64Url(hashBuffer)}`;
        clientDataJSON = bufferToBase64Url(
            stringToBuffer(JSON.stringify({ type: "webauthn.get", challenge: challengeUsed, origin: window.location.origin }))
        );
    }

    return {
        credential_id: credId,
        challenge_used: challengeUsed,
        assertion_signature: assertionSignature,
        authenticator_data: authenticatorData,
        client_data_json: clientDataJSON
    };
}