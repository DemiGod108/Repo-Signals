function show_message(container, message_text, message_type) {
	const existing_message = container.querySelector('.message-banner')

	if (existing_message) {
		existing_message.remove()
	}

	const banner = document.createElement('div')
	banner.classList.add('message-banner')

	if (message_type === 'error') {
		banner.classList.add('message-banner-error')
	}
	else {
		banner.classList.add('message-banner-success')
	}

	const text_element = document.createElement('p')
	text_element.textContent = message_text

	const dismiss_button = document.createElement('button')
	dismiss_button.textContent = 'Dismiss'
	dismiss_button.classList.add('message-banner-dismiss')
	dismiss_button.addEventListener('click', () => {
		banner.remove()
	})

	banner.appendChild(text_element)
	banner.appendChild(dismiss_button)
	container.prepend(banner)
}

export { show_message }