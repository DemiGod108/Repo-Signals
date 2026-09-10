import { BACKEND_URL } from './config.js'
import { authenticated_fetch } from './auth.js'


const repository_list =
	document.getElementById('repository-list')

const repository_count =
	document.getElementById('repository-count')

const add_repository_button =
	document.getElementById('add-repository-button')

const add_repository_modal =
	document.getElementById('add-repository-modal')

const close_modal_button =
	document.getElementById('close-modal-button')

const cancel_add_repository_button =
	document.getElementById('cancel-add-repository-button')

const add_repository_form =
	document.getElementById('add-repository-form')

const repository_name_input =
	document.getElementById('repository-name')

const add_repository_message =
	document.getElementById('add-repository-message')

const submit_add_repository_button =
	document.getElementById('submit-add-repository-button')


function show_repository_loading() {

	repository_list.innerHTML = ''

	const loading_state =
		document.createElement('div')

	loading_state.classList.add(
		'repository-state'
	)

	loading_state.innerHTML = `
		<p>Loading tracked repositories...</p>
	`

	repository_list.appendChild(
		loading_state
	)

	repository_count.textContent =
		'Loading repositories...'
}


function show_repository_error() {

	repository_list.innerHTML = ''

	const error_state =
		document.createElement('div')

	error_state.classList.add(
		'repository-state'
	)

	error_state.innerHTML = `
		<p class="repository-empty-title">
			Unable to load repositories
		</p>

		<p class="repository-empty-description">
			We couldn't retrieve your tracked repositories right now.
			Please try again.
		</p>

		<button
			type="button"
			class="repository-empty-action"
			id="retry-repositories-button"
		>
			Retry
		</button>
	`

	repository_list.appendChild(
		error_state
	)

	repository_count.textContent =
		'Unable to load repositories'

	document
		.getElementById('retry-repositories-button')
		.addEventListener(
			'click',
			load_tracked_repositories
		)
}


function show_empty_state() {

	repository_list.innerHTML = ''

	const empty_state =
		document.createElement('div')

	empty_state.classList.add(
		'repository-state'
	)

	empty_state.innerHTML = `
		<p class="repository-empty-title">
			No repositories tracked yet
		</p>

		<p class="repository-empty-description">
			Add a repository from your GitHub account to start
			receiving repository health and activity signals.
		</p>

		<button
			type="button"
			class="repository-empty-action"
			id="empty-state-add-button"
		>
			Add repository
		</button>
	`

	repository_list.appendChild(
		empty_state
	)

	repository_count.textContent =
		'0 repositories'

	document
		.getElementById('empty-state-add-button')
		.addEventListener(
			'click',
			open_add_repository_modal
		)
}


function create_repository_item(repository) {

	const repository_item =
		document.createElement('div')

	repository_item.classList.add(
		'repository-item'
	)

	repository_item.setAttribute(
		'tabindex',
		'0'
	)

	repository_item.setAttribute(
		'role',
		'link'
	)

	const repository_main =
		document.createElement('div')

	repository_main.classList.add(
		'repository-main'
	)


	const repository_mark =
		document.createElement('div')

	repository_mark.classList.add(
		'repository-mark'
	)

	repository_mark.setAttribute(
		'aria-hidden',
		'true'
	)

	repository_mark.textContent = 'R'


	const repository_info =
		document.createElement('div')

	repository_info.classList.add(
		'repository-info'
	)


	const repository_name =
		document.createElement('p')

	repository_name.classList.add(
		'repository-name'
	)

	repository_name.textContent =
		repository.repo_name


	const repository_meta =
		document.createElement('p')

	repository_meta.classList.add(
		'repository-meta'
	)

	repository_meta.textContent =
		`Repository ID: ${repository.repo_id}`


	repository_info.appendChild(
		repository_name
	)

	repository_info.appendChild(
		repository_meta
	)


	repository_main.appendChild(
		repository_mark
	)

	repository_main.appendChild(
		repository_info
	)


	const repository_action =
		document.createElement('div')

	repository_action.classList.add(
		'repository-action'
	)

	repository_action.innerHTML = `
		<span>View repository</span>
		<span
			class="repository-arrow"
			aria-hidden="true"
		>
			→
		</span>
	`


	repository_item.appendChild(
		repository_main
	)

	repository_item.appendChild(
		repository_action
	)


	const open_repository = () => {

		window.location.assign(
			`./repo.html?id=${encodeURIComponent(repository.repo_id)}`
		)

	}


	repository_item.addEventListener(
		'click',
		open_repository
	)

	repository_item.addEventListener(
		'keydown',
		(event) => {

			if (
				event.key === 'Enter' ||
				event.key === ' '
			) {

				event.preventDefault()

				open_repository()

			}

		}
	)


	return repository_item
}


function show_repositories(repositories) {

	repository_list.innerHTML = ''

	repository_count.textContent =
		`${repositories.length} ${
			repositories.length === 1
				? 'repository'
				: 'repositories'
		}`


	for (const repository of repositories) {

		const repository_item =
			create_repository_item(repository)

		repository_list.appendChild(
			repository_item
		)
	}

}


async function load_tracked_repositories() {

	show_repository_loading()

	try {

		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/display-tracked-repos`
			)


		if (!response.ok) {

			console.error(
				'Repository request failed:',
				response.status
			)

			show_repository_error()

			return

		}


		const data =
			await response.json()

		const repositories =
			Array.isArray(data.tracked_repos)
				? data.tracked_repos
				: []


		if (repositories.length === 0) {

			show_empty_state()

			return

		}


		show_repositories(
			repositories
		)

	}
	catch (error) {

		console.error(
			'Failed to load tracked repositories:',
			error
		)

		/*
		 * authenticated_fetch handles authentication
		 * failures and redirects to login when required.
		 *
		 * Only show the dashboard error when the failure
		 * was an actual request/data failure.
		 */

		if (
			!error.message.includes(
				'Authentication'
			)
		) {

			show_repository_error()

		}

	}

}


/* -------------------------------------------------- */
/* Add Repository Modal */
/* -------------------------------------------------- */

function open_add_repository_modal() {

	add_repository_modal.hidden = false

	add_repository_message.textContent = ''

	add_repository_message.className =
		'form-message'

	repository_name_input.value = ''

	document.body.style.overflow = 'hidden'

	repository_name_input.focus()

}


function close_add_repository_modal() {

	add_repository_modal.hidden = true

	add_repository_message.textContent = ''

	add_repository_message.className =
		'form-message'

	document.body.style.overflow = ''

	add_repository_button.focus()

}


function show_add_repository_message(
	message_text,
	message_type
) {

	add_repository_message.textContent =
		message_text

	add_repository_message.className =
		`form-message form-message-${message_type}`

}


async function handle_add_repository(event) {

	event.preventDefault()


	const repository_name =
		repository_name_input.value.trim()


	if (!repository_name) {

		show_add_repository_message(
			'Please enter a repository name.',
			'error'
		)

		repository_name_input.focus()

		return

	}


	submit_add_repository_button.disabled = true

	submit_add_repository_button.textContent =
		'Adding...'

	show_add_repository_message(
		'',
		'error'
	)


	try {

		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/setup-webhook`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						repo_name: repository_name
					})
				}
			)


		if (response.status === 201) {

			show_add_repository_message(
				'Repository added successfully.',
				'success'
			)


			await load_tracked_repositories()


			setTimeout(() => {

				close_add_repository_modal()

			}, 500)


			return

		}


		if (response.status === 400) {

			show_add_repository_message(
				'This repository is already being tracked.',
				'error'
			)

			return

		}


		if (response.status === 403) {

			show_add_repository_message(
				'You must have admin access to this repository.',
				'error'
			)

			return

		}


		if (response.status === 404) {

			show_add_repository_message(
				'Repository not found in your GitHub account.',
				'error'
			)

			return

		}


		show_add_repository_message(
			'Unable to add this repository. Please try again.',
			'error'
		)

	}
	catch (error) {

		console.error(
			'Failed to add repository:',
			error
		)

		if (
			!error.message.includes(
				'Authentication'
			)
		) {

			show_add_repository_message(
				'Something went wrong. Please try again.',
				'error'
			)

		}

	}
	finally {

		submit_add_repository_button.disabled =
			false

		submit_add_repository_button.textContent =
			'Add repository'

	}

}


/* -------------------------------------------------- */
/* Modal events */
/* -------------------------------------------------- */

add_repository_button.addEventListener(
	'click',
	open_add_repository_modal
)


close_modal_button.addEventListener(
	'click',
	close_add_repository_modal
)


cancel_add_repository_button.addEventListener(
	'click',
	close_add_repository_modal
)


add_repository_form.addEventListener(
	'submit',
	handle_add_repository
)


add_repository_modal.addEventListener(
	'click',
	(event) => {

		if (
			event.target === add_repository_modal
		) {

			close_add_repository_modal()

		}

	}
)


document.addEventListener(
	'keydown',
	(event) => {

		if (
			event.key === 'Escape' &&
			!add_repository_modal.hidden
		) {

			close_add_repository_modal()

		}

	}
)


load_tracked_repositories()