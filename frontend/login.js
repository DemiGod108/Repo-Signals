import { BACKEND_URL } from './config.js'

function set_github_login_link() {
	const login_button = document.getElementById('github-login-button')
	login_button.setAttribute('href', `${BACKEND_URL}/github-auth`)
	login_button.addEventListener('click', show_loading_state)
}

function show_loading_state() {
	const login_button = document.getElementById('github-login-button')
	login_button.classList.add('is-loading')
}

set_github_login_link()