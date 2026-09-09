import { show_message } from './messages.js'

function check_for_oauth_error() {
	const url_params = new URLSearchParams(window.location.search)
	const error_param = url_params.get('error')

	if (error_param) {
		const container = document.getElementById('landing-container')
		show_message(container, 'GitHub sign-in was cancelled or denied. Please try again to continue.', 'error')
	}
}

check_for_oauth_error()