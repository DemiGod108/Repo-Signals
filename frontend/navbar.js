import { BACKEND_URL } from './config.js'

function build_navbar() {
	const navbar = document.createElement('nav')
	navbar.setAttribute('id', 'navbar')

	const logo_link = document.createElement('a')
	logo_link.setAttribute('href', './dashboard.html')
	logo_link.setAttribute('id', 'navbar-logo')
	logo_link.textContent = 'repo-signals'

	const logout_button = document.createElement('button')
	logout_button.setAttribute('id', 'navbar-logout-button')
	logout_button.textContent = 'Log out'
	logout_button.addEventListener('click', handle_logout)

	navbar.appendChild(logo_link)
	navbar.appendChild(logout_button)

	document.body.prepend(navbar)
}

async function handle_logout() {
	try {
		await fetch(`${BACKEND_URL}/logout`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			credentials: 'include'
		})
	}
	catch (error) {
		console.error('Logout request failed:', error)
	}

	window.location.assign('./index.html')
}

build_navbar()