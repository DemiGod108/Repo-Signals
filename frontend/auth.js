import { BACKEND_URL } from './config.js'


async function refresh_access_token() {

	try {

		const response = await fetch(`${BACKEND_URL}/refresh`, {
			method: 'POST',
			credentials: 'include'
		})

		return response.ok

	}
	catch (error) {

		console.error('Token refresh request failed:', error)

		return false

	}

}


function redirect_to_login() {

	window.location.assign('./login.html')

}


async function authenticated_fetch(
	url,
	options = {}
) {

	const refresh_successful =
		await refresh_access_token()


	if (!refresh_successful) {

		redirect_to_login()

		throw new Error('Authentication refresh failed.')

	}


	const request_options = {
		...options,
		credentials: 'include'
	}


	let response

	try {

		response =
			await fetch(url, request_options)

	}
	catch (error) {

		console.error('Authenticated request failed:', error)

		throw error

	}


	if (response.status !== 401) {

		return response

	}


	/*
	 * The access token may have expired between the
	 * refresh request and the protected request.
	 *
	 * Refresh once more and retry the original request.
	 */

	const retry_refresh_successful =
		await refresh_access_token()


	if (!retry_refresh_successful) {

		redirect_to_login()

		throw new Error('Authentication expired.')

	}


	try {

		response =
			await fetch(url, request_options)

	}
	catch (error) {

		console.error('Authenticated retry failed:', error)

		throw error

	}


	if (response.status === 401) {

		redirect_to_login()

		throw new Error('Authentication expired.')

	}


	return response

}


export {
	refresh_access_token,
	authenticated_fetch
}