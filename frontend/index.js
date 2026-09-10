import { show_message } from './messages.js'


function check_for_oauth_error() {

	const url_params =
		new URLSearchParams(window.location.search)

	const error_param =
		url_params.get('error')


	if (error_param) {

		const container =
			document.getElementById('landing-container')


		show_message(
			container,
			'GitHub sign-in was cancelled or denied. Please try again to continue.',
			'error'
		)

	}

}


function remove_oauth_error_from_url() {

	const url =
		new URL(window.location.href)


	if (!url.searchParams.has('error')) {
		return
	}


	url.searchParams.delete('error')


	window.history.replaceState(
		{},
		document.title,
		url.pathname + url.search + url.hash
	)

}


check_for_oauth_error()

remove_oauth_error_from_url()