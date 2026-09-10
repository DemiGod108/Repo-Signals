import { BACKEND_URL } from './config.js'


function build_navbar() {

	const navbar =
		document.createElement('nav')

	navbar.setAttribute('id', 'navbar')


	const navbar_content =
		document.createElement('div')

	navbar_content.setAttribute(
		'id',
		'navbar-content'
	)


	/* -------------------------------------------- */
	/* Brand */
	/* -------------------------------------------- */

	const logo_link =
		document.createElement('a')

	logo_link.setAttribute(
		'href',
		'./dashboard.html'
	)

	logo_link.setAttribute(
		'id',
		'navbar-logo'
	)

	logo_link.setAttribute(
		'aria-label',
		'Repo Signals dashboard'
	)


	const brand_mark =
		document.createElement('span')

	brand_mark.classList.add(
		'navbar-brand-mark'
	)

	brand_mark.setAttribute(
		'aria-hidden',
		'true'
	)


	brand_mark.innerHTML = `
		<svg viewBox="0 0 32 32">
			<path d="M6 22L13 15L18 19L26 10"></path>
			<circle cx="6" cy="22" r="2"></circle>
			<circle cx="13" cy="15" r="2"></circle>
			<circle cx="18" cy="19" r="2"></circle>
			<circle cx="26" cy="10" r="2"></circle>
		</svg>
	`


	const wordmark =
		document.createElement('span')

	wordmark.classList.add(
		'navbar-wordmark'
	)

	wordmark.textContent =
		'Repo Signals'


	logo_link.appendChild(brand_mark)
	logo_link.appendChild(wordmark)


	/* -------------------------------------------- */
	/* Logout */
	/* -------------------------------------------- */

	const logout_button =
		document.createElement('button')

	logout_button.setAttribute(
		'type',
		'button'
	)

	logout_button.setAttribute(
		'id',
		'navbar-logout-button'
	)

	logout_button.setAttribute(
		'aria-label',
		'Log out'
	)


	logout_button.innerHTML = `
		<svg
			class="logout-icon"
			viewBox="0 0 24 24"
			aria-hidden="true"
		>
			<path d="M10 17l5-5-5-5"></path>
			<path d="M15 12H3"></path>
			<path d="M21 19V5a2 2 0 0 0-2-2h-6"></path>
		</svg>

		<span>Log out</span>
	`


	logout_button.addEventListener(
		'click',
		handle_logout
	)


	navbar_content.appendChild(logo_link)
	navbar_content.appendChild(logout_button)

	navbar.appendChild(navbar_content)

	document.body.prepend(navbar)
}


async function handle_logout() {

	const logout_button =
		document.getElementById(
			'navbar-logout-button'
		)


	logout_button.disabled = true
	logout_button.classList.add('is-logging-out')


	try {

		await fetch(`${BACKEND_URL}/logout`, {
			method: 'POST',
			credentials: 'include'
		})

	}
	catch (error) {

		console.error(
			'Logout request failed:',
			error
		)

	}


	window.location.assign('./index.html')
}


build_navbar()