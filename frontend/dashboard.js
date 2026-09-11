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

const close_add_repository_modal_button =
	document.getElementById('close-add-repository-modal')

const cancel_add_repository_button =
	document.getElementById('cancel-add-repository')

const add_repository_form =
	document.getElementById('add-repository-form')

const repository_name_input =
	document.getElementById('repository-name')

const add_repository_message =
	document.getElementById('add-repository-message')

const submit_add_repository_button =
	document.getElementById('submit-add-repository')

const stop_monitoring_modal =
	document.getElementById('stop-monitoring-modal')

const close_stop_monitoring_modal_button =
	document.getElementById('close-stop-monitoring-modal')

const cancel_stop_monitoring_button =
	document.getElementById('cancel-stop-monitoring')

const confirm_stop_monitoring_button =
	document.getElementById('confirm-stop-monitoring')

const stop_monitoring_repository_name =
	document.getElementById('stop-monitoring-repository-name')


let repository_pending_stop = null


/* ---------------------------------------------------------
   Repository state helpers
--------------------------------------------------------- */

function show_repository_loading() {
	repository_list.innerHTML = ''

	const loading_state =
		document.createElement('div')

	loading_state.classList.add(
		'repository-state'
	)

	loading_state.innerHTML = `
		<p>
			Loading tracked repositories...
		</p>
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

	const retry_button =
		document.getElementById(
			'retry-repositories-button'
		)

	retry_button.addEventListener(
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

	const empty_state_add_button =
		document.getElementById(
			'empty-state-add-button'
		)

	empty_state_add_button.addEventListener(
		'click',
		open_add_repository_modal
	)
}


/* ---------------------------------------------------------
   Date formatting
--------------------------------------------------------- */

function format_tracking_date(date_value) {
	if (!date_value) {
		return 'Tracking date unavailable'
	}

	const tracking_date =
		new Date(date_value)

	if (Number.isNaN(tracking_date.getTime())) {
		return 'Tracking date unavailable'
	}

	return new Intl.DateTimeFormat(
		'en-US',
		{
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		}
	).format(tracking_date)
}


/* ---------------------------------------------------------
   Repository item
--------------------------------------------------------- */

function create_repository_item(repository) {
	const repository_item =
		document.createElement('div')

	repository_item.classList.add(
		'repository-row'
	)

	repository_item.setAttribute(
		'tabindex',
		'0'
	)

	repository_item.setAttribute(
		'role',
		'link'
	)

	repository_item.setAttribute(
		'aria-label',
		`Open ${repository.repo_name}`
	)


	const repository_information =
		document.createElement('div')

	repository_information.classList.add(
		'repository-information'
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
		`Tracking since ${format_tracking_date(
			repository.tracking_started_at
		)}`


	repository_information.appendChild(
		repository_name
	)

	repository_information.appendChild(
		repository_meta
	)


	const repository_actions =
		document.createElement('div')

	repository_actions.classList.add(
		'repository-actions'
	)


	const view_repository_action =
		document.createElement('div')

	view_repository_action.classList.add(
		'repository-action',
		'repository-view-action'
	)

	view_repository_action.setAttribute(
		'role',
		'link'
	)

	view_repository_action.setAttribute(
		'tabindex',
		'0'
	)

	view_repository_action.setAttribute(
		'aria-label',
		`View ${repository.repo_name}`
	)

	view_repository_action.innerHTML = `
		<span>View repository</span>
		<span aria-hidden="true">→</span>
	`


	const stop_monitoring_button =
		document.createElement('button')

	stop_monitoring_button.type =
		'button'

	stop_monitoring_button.classList.add(
		'repository-action',
		'stop-monitoring-button'
	)

	stop_monitoring_button.textContent =
		'Stop monitoring'

	stop_monitoring_button.setAttribute(
		'aria-label',
		`Stop monitoring ${repository.repo_name}`
	)


	const open_repository = () => {
		window.location.assign(
			`./repo.html?id=${encodeURIComponent(
				repository.repo_id
			)}`
		)
	}


	view_repository_action.addEventListener(
		'click',
		(event) => {
			event.stopPropagation()
			open_repository()
		}
	)


	view_repository_action.addEventListener(
		'keydown',
		(event) => {
			if (
				event.key === 'Enter' ||
				event.key === ' '
			) {
				event.preventDefault()
				event.stopPropagation()
				open_repository()
			}
		}
	)


	stop_monitoring_button.addEventListener(
		'click',
		(event) => {
			event.stopPropagation()
			open_stop_monitoring_modal(repository)
		}
	)


	repository_actions.appendChild(
		view_repository_action
	)

	repository_actions.appendChild(
		stop_monitoring_button
	)


	repository_item.appendChild(
		repository_information
	)

	repository_item.appendChild(
		repository_actions
	)


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


/* ---------------------------------------------------------
   Render repositories
--------------------------------------------------------- */

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


/* ---------------------------------------------------------
   Load repositories
--------------------------------------------------------- */

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

		if (
			!error.message.includes(
				'Authentication'
			)
		) {
			show_repository_error()
		}
	}
}


/* ---------------------------------------------------------
   Add repository modal
--------------------------------------------------------- */

function open_add_repository_modal() {
	add_repository_modal.hidden =
		false

	add_repository_message.textContent =
		''

	add_repository_message.className =
		'form-message'

	repository_name_input.value =
		''

	document.body.style.overflow =
		'hidden'

	repository_name_input.focus()
}


function close_add_repository_modal() {
	add_repository_modal.hidden =
		true

	add_repository_message.textContent =
		''

	add_repository_message.className =
		'form-message'

	document.body.style.overflow =
		''

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


	submit_add_repository_button.disabled =
		true

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
						'Content-Type':
							'application/json'
					},
					body: JSON.stringify({
						repo_name:
							repository_name
					})
				}
			)


		if (response.status === 201) {
			show_add_repository_message(
				'Repository added successfully.',
				'success'
			)

			await load_tracked_repositories()

			setTimeout(
				close_add_repository_modal,
				500
			)

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


/* ---------------------------------------------------------
   Stop monitoring modal
--------------------------------------------------------- */

function open_stop_monitoring_modal(repository) {
	repository_pending_stop =
		repository

	stop_monitoring_repository_name.textContent =
		repository.repo_name

	stop_monitoring_modal.hidden =
		false

	document.body.style.overflow =
		'hidden'

	confirm_stop_monitoring_button.focus()
}


function close_stop_monitoring_modal() {
	stop_monitoring_modal.hidden =
		true

	repository_pending_stop =
		null

	document.body.style.overflow =
		''

	load_tracked_repositories()
}


async function handle_stop_monitoring() {
	if (!repository_pending_stop) {
		return
	}


	const repository =
		repository_pending_stop

	confirm_stop_monitoring_button.disabled =
		true

	confirm_stop_monitoring_button.textContent =
		'Stopping...'


	try {
		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/stop-monitoring/${encodeURIComponent(
					repository.repo_id
				)}`,
				{
					method: 'DELETE'
				}
			)


		if (response.status === 200) {
			close_stop_monitoring_modal()
			return
		}


		if (response.status === 400) {
			alert(
				'This repository is not currently being monitored.'
			)
			return
		}


		if (response.status === 404) {
			alert(
				'The webhook for this repository was not found. The repository was not removed from Repo Signals.'
			)
			return
		}


		alert(
			'Unable to stop monitoring this repository. Please try again.'
		)
	}
	catch (error) {
		console.error(
			'Failed to stop monitoring repository:',
			error
		)

		if (
			!error.message.includes(
				'Authentication'
			)
		) {
			alert(
				'Something went wrong while stopping monitoring. Please try again.'
			)
		}
	}
	finally {
		confirm_stop_monitoring_button.disabled =
			false

		confirm_stop_monitoring_button.textContent =
			'Stop monitoring'
	}
}


/* ---------------------------------------------------------
   Modal events
--------------------------------------------------------- */

add_repository_button.addEventListener(
	'click',
	open_add_repository_modal
)


close_add_repository_modal_button.addEventListener(
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
			event.target ===
			add_repository_modal
		) {
			close_add_repository_modal()
		}
	}
)


close_stop_monitoring_modal_button.addEventListener(
	'click',
	close_stop_monitoring_modal
)


cancel_stop_monitoring_button.addEventListener(
	'click',
	close_stop_monitoring_modal
)


confirm_stop_monitoring_button.addEventListener(
	'click',
	handle_stop_monitoring
)


stop_monitoring_modal.addEventListener(
	'click',
	(event) => {
		if (
			event.target ===
			stop_monitoring_modal
		) {
			close_stop_monitoring_modal()
		}
	}
)


document.addEventListener(
	'keydown',
	(event) => {
		if (event.key !== 'Escape') {
			return
		}


		if (!add_repository_modal.hidden) {
			close_add_repository_modal()
			return
		}


		if (!stop_monitoring_modal.hidden) {
			close_stop_monitoring_modal()
		}
	}
)


/* ---------------------------------------------------------
   Initial load
--------------------------------------------------------- */

load_tracked_repositories()