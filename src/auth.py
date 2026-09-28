import streamlit as st


# Prototype authentication validates credential format only. It must be
# replaced by a proper authentication service before production use.
AUTHENTICATED_KEY = "paimana_authenticated"
OFFICER_EMAIL_KEY = "paimana_officer_email"
OFFICER_ROLE_KEY = "paimana_officer_role"
OFFICER_ROLE = "Monitoring Officer"


def is_authenticated() -> bool:
    """Return whether the current Streamlit session is authenticated."""
    return bool(st.session_state.get(AUTHENTICATED_KEY, False))


def _is_valid_email(email: str) -> bool:
    """Apply the simple email check required for the demo prototype."""
    if email.count("@") != 1 or any(character.isspace() for character in email):
        return False

    local_part, domain = email.split("@", maxsplit=1)
    return bool(
        local_part
        and domain
        and "." in domain
        and not domain.startswith(".")
        and not domain.endswith(".")
    )


def _is_valid_password(password: str) -> bool:
    """Apply the transparent password-format rules used by the prototype."""
    return bool(
        len(password) >= 8
        and any(character.isupper() for character in password)
        and any(character.islower() for character in password)
        and any(character.isdigit() for character in password)
        and any(not character.isalnum() for character in password)
    )


def authenticate(officer_id: str, password: str) -> bool:
    """Check the prototype credentials and update the current session."""
    normalized_email = officer_id.strip().lower()
    officer_matches = _is_valid_email(normalized_email)
    password_matches = _is_valid_password(password)
    authenticated = officer_matches and password_matches
    st.session_state[AUTHENTICATED_KEY] = authenticated

    if authenticated:
        st.session_state[OFFICER_EMAIL_KEY] = normalized_email
        st.session_state[OFFICER_ROLE_KEY] = OFFICER_ROLE
    else:
        st.session_state.pop(OFFICER_EMAIL_KEY, None)
        st.session_state.pop(OFFICER_ROLE_KEY, None)

    return authenticated


def logout() -> None:
    """Remove all session values so the user returns to a clean login screen."""
    st.session_state.clear()
