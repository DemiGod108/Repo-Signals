import { BACKEND_URL } from './config.js'
import { authenticated_fetch } from './auth.js'

const repository_id = get_repository_id_from_url()

let current_repository = null
let activity_source = null
let bus_factor_chart = null
let activity_trend_chart = null
let health_metrics_loaded = false
let activity_graph_loaded = false


function get_repository_id_from_url() {
	const url_params = new URLSearchParams(window.location.search)
	const repo_id = url_params.get('id')

	if (!repo_id) {
		window.location.assign('./dashboard.html')
		throw new Error('Repository ID is missing from the URL.')
	}

	return repo_id
}


/* ------------------------------------------------------------ */
/* Utility functions                                             */
/* ------------------------------------------------------------ */

function show_element(element_id) {
	const element = document.getElementById(element_id)

	if (element) {
		element.hidden = false
	}
}


function hide_element(element_id) {
	const element = document.getElementById(element_id)

	if (element) {
		element.hidden = true
	}
}


function format_tracking_date(date_value) {
	if (!date_value) {
		return 'Tracking date unavailable'
	}

	const parsed_date = new Date(date_value)

	if (Number.isNaN(parsed_date.getTime())) {
		return 'Tracking date unavailable'
	}

	return `Tracking since ${parsed_date.toLocaleDateString(undefined, {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	})}`
}


function format_number(value) {
	if (
		value === null ||
		value === undefined ||
		value === ''
	) {
		return '0'
	}

	const number_value = Number(value)

	if (Number.isNaN(number_value)) {
		return '0'
	}

	return number_value.toLocaleString()
}


function format_percentage(value) {
	const number_value = Number(value)

	if (Number.isNaN(number_value)) {
		return '—'
	}

	return `${number_value.toFixed(1)}%`
}


function format_days(value) {
	if (
		value === null ||
		value === undefined ||
		value === '' ||
		value === 'insufficient data' ||
		value === 'No sufficent data yet'
	) {
		return 'Insufficient data'
	}

	const number_value = Number(value)

	if (Number.isNaN(number_value)) {
		return String(value)
	}

	if (number_value === 1) {
		return '1 day'
	}

	return `${number_value.toFixed(1)} days`
}


function is_insufficient_data(value) {
	return (
		value === null ||
		value === undefined ||
		value === '' ||
		value === 'insufficient data' ||
		value === 'No sufficent data yet'
	)
}


/* ------------------------------------------------------------ */
/* Repository information                                       */
/* ------------------------------------------------------------ */

function set_repository_header() {
	if (!current_repository) {
		return
	}

	document.getElementById(
		'repository-title'
	).textContent =
		current_repository.repo_name

	document.getElementById(
		'repository-subtitle'
	).textContent =
		format_tracking_date(
			current_repository.tracking_started_at
		)
}


async function load_repository_information() {
	try {
		const response = await authenticated_fetch(
			`${BACKEND_URL}/display-tracked-repos`
		)

		if (!response.ok) {
			throw new Error(
				`Repository list request failed with status ${response.status}.`
			)
		}

		const data = await response.json()

		const repositories = Array.isArray(
			data.tracked_repos
		)
			? data.tracked_repos
			: []

		current_repository = repositories.find(
			repository =>
				String(repository.repo_id) ===
				String(repository_id)
		)

		if (!current_repository) {
			throw new Error(
				'Repository is not being tracked.'
			)
		}

		set_repository_header()
	}
	catch (error) {
		console.error(
			'Failed to load repository information:',
			error
		)

		document.getElementById(
			'repository-title'
		).textContent =
			'Repository unavailable'

		document.getElementById(
			'repository-subtitle'
		).textContent =
			'This repository is no longer available in your tracked repositories.'
	}
}


/* ------------------------------------------------------------ */
/* Tabs                                                          */
/* ------------------------------------------------------------ */

function activate_repository_tab(tab_name) {
	const overview_tab =
		document.getElementById(
			'overview-tab'
		)

	const health_metrics_tab =
		document.getElementById(
			'health-metrics-tab'
		)

	const overview_panel =
		document.getElementById(
			'overview-panel'
		)

	const health_metrics_panel =
		document.getElementById(
			'health-metrics-panel'
		)


	if (tab_name === 'health-metrics') {
		overview_tab.classList.remove(
			'is-active'
		)

		health_metrics_tab.classList.add(
			'is-active'
		)


		overview_tab.setAttribute(
			'aria-selected',
			'false'
		)

		health_metrics_tab.setAttribute(
			'aria-selected',
			'true'
		)


		overview_panel.hidden = true
		health_metrics_panel.hidden = false


		if (!health_metrics_loaded) {
			load_health_metrics()
		}

		if (!activity_graph_loaded) {
			load_activity_graph()
		}

		return
	}


	overview_tab.classList.add(
		'is-active'
	)

	health_metrics_tab.classList.remove(
		'is-active'
	)


	overview_tab.setAttribute(
		'aria-selected',
		'true'
	)

	health_metrics_tab.setAttribute(
		'aria-selected',
		'false'
	)


	overview_panel.hidden = false
	health_metrics_panel.hidden = true
}


function initialize_tabs() {
	const overview_tab =
		document.getElementById(
			'overview-tab'
		)

	const health_metrics_tab =
		document.getElementById(
			'health-metrics-tab'
		)


	if (
		!overview_tab ||
		!health_metrics_tab
	) {
		console.error(
			'Repository tabs could not be initialized.'
		)

		return
	}


	overview_tab.addEventListener(
		'click',
		function () {
			activate_repository_tab(
				'overview'
			)
		}
	)


	health_metrics_tab.addEventListener(
		'click',
		function () {
			activate_repository_tab(
				'health-metrics'
			)
		}
	)
}


/* ------------------------------------------------------------ */
/* Overview                                                      */
/* ------------------------------------------------------------ */

function set_overview_reload_state(is_loading) {
	const reload_button =
		document.getElementById(
			'reload-overview-button'
		)

	if (!reload_button) {
		return
	}

	reload_button.disabled = is_loading

	reload_button.classList.toggle(
		'is-loading',
		is_loading
	)
}


async function load_overview() {
	const overview_grid =
		document.getElementById(
			'overview-grid'
		)

	const has_existing_data =
		!overview_grid.hidden


	set_overview_reload_state(
		true
	)

	hide_element(
		'overview-error-state'
	)


	if (!has_existing_data) {
		show_element(
			'overview-loading-state'
		)
	}


	try {
		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/overview/${encodeURIComponent(repository_id)}`
			)


		if (!response.ok) {
			throw new Error(
				`Overview request failed with status ${response.status}.`
			)
		}


		const response_data =
			await response.json()

		const overview =
			response_data.repo_overview


		if (!overview) {
			throw new Error(
				'Repository overview data is missing from the response.'
			)
		}


		document.getElementById(
			'overview-commits'
		).textContent =
			format_number(
				overview.total_num_commits
			)


		document.getElementById(
			'overview-forks'
		).textContent =
			format_number(
				overview.total_num_forks
			)


		document.getElementById(
			'overview-open-pull-requests'
		).textContent =
			format_number(
				overview.total_num_open_prs
			)


		document.getElementById(
			'overview-open-issues'
		).textContent =
			format_number(
				overview.total_num_open_issues
			)


		hide_element(
			'overview-loading-state'
		)

		hide_element(
			'overview-error-state'
		)

		show_element(
			'overview-grid'
		)
	}
	catch (error) {
		console.error(
			'Failed to load repository overview:',
			error
		)

		hide_element(
			'overview-loading-state'
		)

		show_element(
			'overview-error-state'
		)


		if (!has_existing_data) {
			hide_element(
				'overview-grid'
			)
		}
	}
	finally {
		set_overview_reload_state(
			false
		)
	}
}


/* ------------------------------------------------------------ */
/* Health metrics                                                 */
/* ------------------------------------------------------------ */

function set_health_reload_state(is_loading) {
	const reload_button =
		document.getElementById(
			'reload-health-button'
		)

	if (!reload_button) {
		return
	}

	reload_button.disabled = is_loading

	reload_button.classList.toggle(
		'is-loading',
		is_loading
	)
}


function normalize_health_data(data) {
	const health_data = data || {}

	return {
		spike_decline_metric:
			health_data.spike_decline_metric,

		pr_lifecycle_health:
			health_data.pr_lifecycle_health,

		bus_factor:
			health_data.bus_factor,

		stale_issue:
			health_data.stale_issue
	}
}

async function load_health_metrics() {
	const health_content =
		document.getElementById(
			'health-content'
		)

	const has_existing_data =
		!health_content.hidden

	set_health_reload_state(
		true
	)

	hide_element(
		'health-error-state'
	)

	if (!has_existing_data) {
		show_element(
			'health-loading-state'
		)
	}

	try {
		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/health-metrics/${encodeURIComponent(repository_id)}`
			)

		if (!response.ok) {
			throw new Error(
				`Health metrics request failed with status ${response.status}.`
			)
		}

		const response_data =
			await response.json()

		const health_data =
			normalize_health_data(
				response_data
			)

		update_spike_decline_metric(
			health_data.spike_decline_metric
		)

		update_pr_lifecycle_metric(
			health_data.pr_lifecycle_health
		)

		update_bus_factor_metric(
			health_data.bus_factor
		)

		update_stale_issues_metric(
			health_data.stale_issue
		)

		hide_element(
			'health-loading-state'
		)

		hide_element(
			'health-error-state'
		)

		show_element(
			'health-content'
		)

		health_metrics_loaded = true
	}
	catch (error) {
		console.error(
			'Failed to load health metrics:',
			error
		)

		hide_element(
			'health-loading-state'
		)

		show_element(
			'health-error-state'
		)

		if (!has_existing_data) {
			hide_element(
				'health-content'
			)
		}
	}
	finally {
		set_health_reload_state(
			false
		)
	}
}


/* ------------------------------------------------------------ */
/* Spike / decline                                               */
/* ------------------------------------------------------------ */

function update_spike_decline_metric(value) {
	const status_element =
		document.getElementById(
			'spike-decline-status'
		)

	const description_element =
		document.getElementById(
			'spike-decline-description'
		)


	status_element.classList.remove(
		'status-good',
		'status-bad',
		'status-neutral'
	)


	if (
		is_insufficient_data(
			value
		) 
	) {
		status_element.textContent =
			'Insufficient data'

		status_element.classList.add(
			'status-neutral'
		)

		description_element.textContent =
			'There is not enough collected activity to determine whether repository activity is increasing or decreasing.'

		refresh_activity_graph_colors()

		return
	}


	const normalized_value =
		String(value).toLowerCase()


	if (
		normalized_value === 'spike'
	) {
		status_element.textContent =
			'Spike'

		status_element.classList.add(
			'status-good'
		)

		description_element.textContent =
			'Repository activity is currently showing a significant increase.'
	}
	else if (
		normalized_value === 'decline'
	) {
		status_element.textContent =
			'Decline'

		status_element.classList.add(
			'status-bad'
		)

		description_element.textContent =
			'Repository activity is currently showing a significant decrease.'
	}
	else if (
		normalized_value === 'normal'
	) {
		status_element.textContent =
			'Normal'

		status_element.classList.add(
			'status-neutral'
		)

		description_element.textContent =
			'Repository activity is currently within the expected range.'
	}
	else {
		status_element.textContent =
			String(value)

		status_element.classList.add(
			'status-neutral'
		)

		description_element.textContent =
			'The repository activity trend returned an unrecognized status.'
	}
	refresh_activity_graph_colors()
}


/* ------------------------------------------------------------ */
/* PR lifecycle                                                  */
/* ------------------------------------------------------------ */

function update_pr_lifecycle_metric(data) {
	const merge_element =
		document.getElementById(
			'average-time-to-merge'
		)

	const review_element =
		document.getElementById(
			'average-time-to-review'
		)

	const description_element =
		document.getElementById(
			'pr-lifecycle-description'
		)


	if (
		!data ||
		data === 'insufficient data' ||
		data === 'No sufficent data yet'
	) {
		merge_element.textContent =
			'Insufficient data'

		review_element.textContent =
			'Insufficient data'

		description_element.textContent =
			'There is not enough pull request history to calculate lifecycle averages.'

		return
	}


	const has_merge_data =
		!is_insufficient_data(
			data.avg_time_to_merge
		)

	const has_review_data =
		!is_insufficient_data(
			data.avg_time_to_review
		)


	merge_element.textContent =
		has_merge_data
			? format_days(
				data.avg_time_to_merge
			)
			: 'Insufficient data'


	review_element.textContent =
		has_review_data
			? format_days(
				data.avg_time_to_review
			)
			: 'Insufficient data'


	if (
		!has_merge_data &&
		!has_review_data
	) {
		description_element.textContent =
			'There is not enough pull request history to calculate lifecycle averages.'

		return
	}


	description_element.textContent =
		'Average lifecycle times are calculated from the pull request activity collected for this repository.'
}


/* ------------------------------------------------------------ */
/* Bus factor                                                    */
/* ------------------------------------------------------------ */

function destroy_bus_factor_chart() {
	if (!bus_factor_chart) {
		return
	}

	bus_factor_chart.destroy()
	bus_factor_chart = null
}


function get_bus_factor_data(data) {
	const labels = []
	const values = []

	if (!Array.isArray(data)) {
		return {
			labels,
			values
		}
	}


	data.forEach(
		contributor => {
			if (
				!contributor ||
				typeof contributor !== 'object'
			) {
				return
			}


			const entries =
				Object.entries(
					contributor
				)


			if (entries.length === 0) {
				return
			}


			const name =
				entries[0][0]

			const percentage =
				Number(
					entries[0][1]
				)


			if (
				!name ||
				Number.isNaN(percentage)
			) {
				return
			}


			labels.push(
				name
			)

			values.push(
				percentage
			)
		}
	)


	return {
		labels,
		values
	}
}


function build_bus_factor_legend(
	labels,
	values
) {
	const legend_container =
		document.getElementById(
			'bus-factor-legend'
		)

	legend_container.replaceChildren()


	const chart_colors = [
		'#4f8ff7',
		'#7aa9f8',
		'#9dbdf7',
		'#c0d1f5',
		'#6b7f9d',
		'#4d5b70',
		'#394555'
	]


	labels.forEach(
		(label, index) => {
			const item =
				document.createElement(
					'div'
				)

			item.classList.add(
				'bus-factor-legend-item'
			)


			const name_container =
				document.createElement(
					'div'
				)

			name_container.classList.add(
				'bus-factor-legend-name'
			)


			const marker =
				document.createElement(
					'span'
				)

			marker.classList.add(
				'bus-factor-legend-marker'
			)

			marker.style.backgroundColor =
				chart_colors[
					index %
					chart_colors.length
				]


			const name_element =
				document.createElement(
					'span'
				)

			name_element.textContent =
				label


			name_container.appendChild(
				marker
			)

			name_container.appendChild(
				name_element
			)


			const value_element =
				document.createElement(
					'span'
				)

			value_element.classList.add(
				'bus-factor-legend-value'
			)

			value_element.textContent =
				format_percentage(
					values[index]
				)


			item.appendChild(
				name_container
			)

			item.appendChild(
				value_element
			)

			legend_container.appendChild(
				item
			)
		}
	)
}


function update_bus_factor_metric(data) {
	const canvas =
		document.getElementById(
			'bus-factor-chart'
		)

	const chart_empty_state =
		document.getElementById(
			'bus-factor-chart-empty'
		)

	const legend_container =
		document.getElementById(
			'bus-factor-legend'
		)


	destroy_bus_factor_chart()

	legend_container.replaceChildren()

	hide_element(
		'bus-factor-chart-empty'
	)


	const {
		labels,
		values
	} =
		get_bus_factor_data(
			data
		)


	if (
		labels.length === 0 ||
		values.length === 0
	) {
		show_element(
			'bus-factor-chart-empty'
		)

		return
	}


	build_bus_factor_legend(
		labels,
		values
	)


	if (typeof Chart === 'undefined') {
		console.error(
			'Chart.js is not available.'
		)

		show_element(
			'bus-factor-chart-empty'
		)

		chart_empty_state.querySelector(
			'p'
		).textContent =
			'Chart unavailable'

		return
	}


	const chart_colors = [
		'#4f8ff7',
		'#7aa9f8',
		'#9dbdf7',
		'#c0d1f5',
		'#6b7f9d',
		'#4d5b70',
		'#394555'
	]


	bus_factor_chart =
		new Chart(
			canvas,
			{
				type: 'doughnut',

				data: {
					labels,

					datasets: [
						{
							data: values,

							backgroundColor:
								labels.map(
									(_, index) =>
										chart_colors[
											index %
											chart_colors.length
										]
								),

							borderColor:
								'#1c1c1c',

							borderWidth: 3,

							hoverOffset: 6
						}
					]
				},

				options: {
					responsive: true,
					maintainAspectRatio: false,

					cutout: '68%',

					plugins: {
						legend: {
							display: false
						},

						tooltip: {
							callbacks: {
								label(context) {
									return `${context.label}: ${Number(
										context.parsed
									).toFixed(1)}%`
								}
							}
						}
					}
				}
			}
		)
}


/* ------------------------------------------------------------ */
/* Stale issues                                                  */
/* ------------------------------------------------------------ */

function create_metric_empty_message(
	message
) {
	const element =
		document.createElement(
			'p'
		)

	element.classList.add(
		'metric-empty-state'
	)

	element.textContent =
		message

	return element
}


function update_stale_issues_metric(data) {
	const container =
		document.getElementById(
			'stale-issues-content'
		)

	const summary_column =
		container.querySelector(
			'.stale-issues-summary-column'
		)

	const list_column =
		container.querySelector(
			'.stale-issues-list-column'
		)


	summary_column.replaceChildren()
	list_column.replaceChildren()


	if (
		!data ||
		data === 'insufficient data' ||
		data === 'No sufficent data yet'
	) {
		summary_column.appendChild(
			create_metric_empty_message(
				'There is not enough issue history to determine stale issues.'
			)
		)

		return
	}


	const percentage =
		Number(
			data.percentage_stale
		)


	if (Number.isNaN(percentage)) {
		summary_column.appendChild(
			create_metric_empty_message(
				'Stale issue data is currently unavailable.'
			)
		)

		return
	}


	const valid_percentage =
		Math.min(
			Math.max(
				percentage,
				0
			),
			100
		)


	const percentage_element =
		document.createElement(
			'p'
		)

	percentage_element.classList.add(
		'stale-issues-percentage'
	)

	percentage_element.textContent =
		format_percentage(
			percentage
		)


	const label_element =
		document.createElement(
			'p'
		)

	label_element.classList.add(
		'stale-issues-label'
	)

	label_element.textContent =
		'of tracked issues are stale'


	const track =
		document.createElement(
			'div'
		)

	track.classList.add(
		'stale-issues-track'
	)


	const fill =
		document.createElement(
			'div'
		)

	fill.classList.add(
		'stale-issues-fill'
	)

	fill.style.width =
		`${valid_percentage}%`


	track.appendChild(
		fill
	)


	summary_column.appendChild(
		percentage_element
	)

	summary_column.appendChild(
		label_element
	)

	summary_column.appendChild(
		track
	)


	if (
		Array.isArray(
			data.stale_issues
		) &&
		data.stale_issues.length > 0
	) {
		const list_heading =
			document.createElement(
				'p'
			)

		list_heading.classList.add(
			'stale-issues-list-heading'
		)

		list_heading.textContent =
			'Stale issues'


		const list =
			document.createElement(
				'div'
			)

		list.classList.add(
			'stale-issues-list'
		)


		data.stale_issues.forEach(
			issue_number => {
				const issue_element =
					document.createElement(
						'span'
					)

				issue_element.classList.add(
					'stale-issue-link'
				)

				issue_element.textContent =
					`#${issue_number}`

				list.appendChild(
					issue_element
				)
			}
		)


		list_column.appendChild(
			list_heading
		)

		list_column.appendChild(
			list
		)
	}
	else {
		list_column.appendChild(
			create_metric_empty_message(
				'No stale issues are currently reported.'
			)
		)
	}
}


/* ------------------------------------------------------------ */
/* Activity graph                                                 */
/* ------------------------------------------------------------ */

function destroy_activity_trend_chart() {
	if (!activity_trend_chart) {
		return
	}

	activity_trend_chart.destroy()
	activity_trend_chart = null
}


function set_activity_graph_state(state) {
	hide_element(
		'activity-graph-loading'
	)

	hide_element(
		'activity-graph-error'
	)

	hide_element(
		'activity-graph-insufficient-data'
	)

	hide_element(
		'activity-graph-container'
	)


	if (state === 'loading') {
		show_element(
			'activity-graph-loading'
		)
	}
	else if (state === 'error') {
		show_element(
			'activity-graph-error'
		)
	}
	else if (state === 'insufficient-data') {
		show_element(
			'activity-graph-insufficient-data'
		)
	}
	else if (state === 'success') {
		show_element(
			'activity-graph-container'
		)
	}
}


function get_activity_bar_colors(
	spike_decline_metric,
	count_length
) {
	const default_color =
		'rgba(79, 143, 247, 0.45)'

	const spike_color =
		'#e5534b'

	const decline_color =
		'#5aa9ff'

	const colors =
		Array(count_length).fill(
			default_color
		)

	if (count_length === 0) {
		return colors
	}

	const last_index =
		count_length - 1

	if (
		spike_decline_metric === 'spike'
	) {
		colors[last_index] =
			spike_color
	}
	else if (
		spike_decline_metric === 'decline'
	) {
		colors[last_index] =
			decline_color
	}

	return colors
}


function format_graph_date_label(date_value) {
	const parsed_date =
		new Date(
			`${date_value}T00:00:00Z`
		)

	if (
		Number.isNaN(
			parsed_date.getTime()
		)
	) {
		return date_value
	}

	return parsed_date.toLocaleDateString(
		undefined,
		{
			month: 'short',
			day: 'numeric',
			timeZone: 'UTC'
		}
	)
}


function validate_activity_graph_response(
	response_data
) {
	if (
		!response_data ||
		!Array.isArray(
			response_data.dates
		) ||
		!Array.isArray(
			response_data.count
		)
	) {
		throw new Error(
			'Activity graph response is missing dates or count arrays.'
		)
	}


	if (
		response_data.dates.length === 0 ||
		response_data.count.length === 0
	) {
		throw new Error(
			'Activity graph response contains no data points.'
		)
	}


	if (
		response_data.dates.length !==
		response_data.count.length
	) {
		throw new Error(
			'Activity graph dates and count arrays are not the same length.'
		)
	}


	response_data.dates.forEach(
		date_value => {
			if (
				typeof date_value !== 'string' ||
				!/^\d{4}-\d{2}-\d{2}$/.test(
					date_value
				)
			) {
				throw new Error(
					'Activity graph contains an invalid date.'
				)
			}
		}
	)


	response_data.count.forEach(
		count_value => {
			if (
				!Number.isInteger(
					count_value
				) ||
				count_value < 0
			) {
				throw new Error(
					'Activity graph contains an invalid event count.'
				)
			}
		}
	)


	return {
		dates: response_data.dates,
		counts: response_data.count
	}
}


function render_activity_trend_chart(
	dates,
	counts,
	spike_decline_metric
) {
	const canvas =
		document.getElementById(
			'activity-trend-chart'
		)


	if (typeof Chart === 'undefined') {
		throw new Error(
			'Chart.js is not available.'
		)
	}


	destroy_activity_trend_chart()


	const background_colors =
		get_activity_bar_colors(
			String(
				spike_decline_metric || ''
			).toLowerCase(),
			counts.length
		)


	const max_count =
		Math.max(
			...counts,
			0
		)


	activity_trend_chart =
		new Chart(
			canvas,
			{
				type: 'bar',

				data: {
					labels: dates,

					datasets: [
						{
							data: counts,

							backgroundColor:
								background_colors,

							borderColor:
								background_colors,

							borderWidth: 1,

							borderRadius: 3,

							borderSkipped: false,

							maxBarThickness: 28
						}
					]
				},

				options: {
					responsive: true,
					maintainAspectRatio: false,

					interaction: {
						intersect: false,
						mode: 'index'
					},

					plugins: {
						legend: {
							display: false
						},

						tooltip: {
							displayColors: false,

							callbacks: {
								title(context) {
									const index =
										context[0].dataIndex

									return dates[index]
								},

								label(context) {
									const count =
										context.parsed.y

									const suffix =
										count === 1
											? 'event'
											: 'events'

									return `${count} ${suffix}`
								}
							}
						}
					},

					scales: {
						x: {
							type: 'category',

							grid: {
								display: false
							},

							ticks: {
								color: '#8f8f8f',

								autoSkip: true,

								maxTicksLimit: 10,

								callback(value) {
									const label =
										this.getLabelForValue(
											value
										)

									return format_graph_date_label(
										label
									)
								}
							},

							border: {
								color: '#303238'
							}
						},

						y: {
							beginAtZero: true,

							ticks: {
								color: '#8f8f8f',
								precision: 0,

								stepSize:
									max_count <= 10
										? 1
										: undefined
							},

							grid: {
								color: 'rgba(255, 255, 255, 0.06)'
							},

							border: {
								display: false
							}
						}
					}
				}
			}
		)
}


async function load_activity_graph() {
	const graph_container =
		document.getElementById(
			'activity-graph-container'
		)

	const had_existing_chart =
		activity_trend_chart !== null


	activity_graph_loaded = false

	set_activity_graph_state(
		'loading'
	)


	try {
		const response =
			await authenticated_fetch(
				`${BACKEND_URL}/graph/${encodeURIComponent(repository_id)}`
			)


		if (response.status === 404) {
			let error_data = null

			try {
				error_data =
					await response.json()
			}
			catch (parse_error) {
				error_data = null
			}


			if (
				error_data &&
				error_data.detail ===
				'insufficient data'
			) {
				destroy_activity_trend_chart()

				set_activity_graph_state(
					'insufficient-data'
				)

				activity_graph_loaded = true

				return
			}
		}


		if (!response.ok) {
			throw new Error(
				`Activity graph request failed with status ${response.status}.`
			)
		}


		const response_data =
			await response.json()


		const {
			dates,
			counts
		} =
			validate_activity_graph_response(
				response_data
			)


		/*
			The graph colors use the same spike/decline
			verdict displayed above the chart.

			The health endpoint is queried separately, so
			if it has not loaded yet we simply render all
			bars with the default color.
		*/
		let spike_decline_metric = null

		const status_element =
			document.getElementById(
				'spike-decline-status'
			)

		if (
			status_element &&
			status_element.textContent
		) {
			const status_text =
				status_element.textContent
					.trim()
					.toLowerCase()

			if (
				status_text === 'spike' ||
				status_text === 'decline' ||
				status_text === 'normal'
			) {
				spike_decline_metric =
					status_text
			}
		}


		render_activity_trend_chart(
			dates,
			counts,
			spike_decline_metric
		)


		hide_element(
			'activity-graph-loading'
		)

		hide_element(
			'activity-graph-error'
		)

		hide_element(
			'activity-graph-insufficient-data'
		)

		show_element(
			'activity-graph-container'
		)


		activity_graph_loaded = true
	}
	catch (error) {
		console.error(
			'Failed to load activity graph:',
			error
		)

		/*
			If the server says insufficient data, that state
			has already been handled above.

			All other failures use the graph-specific error
			state and do not affect the other health metrics.
		*/
		set_activity_graph_state(
			'error'
		)

		if (!had_existing_chart) {
			destroy_activity_trend_chart()
		}
	}
}


function refresh_activity_graph_colors() {
	if (!activity_trend_chart) {
		return
	}


	const status_element =
		document.getElementById(
			'spike-decline-status'
		)


	if (!status_element) {
		return
	}


	const status_text =
		status_element.textContent
			.trim()
			.toLowerCase()


	const dataset =
		activity_trend_chart.data.datasets[0]

	const data_length =
		dataset.data.length


	dataset.backgroundColor =
		get_activity_bar_colors(
			status_text,
			data_length
		)

	dataset.borderColor =
		dataset.backgroundColor


	activity_trend_chart.update()
}


/* ------------------------------------------------------------ */
/* Live feed                                                     */
/* ------------------------------------------------------------ */

function set_activity_connection_status(
	status,
	text
) {
	const status_element =
		document.getElementById(
			'activity-connection-status'
		)

	status_element.textContent =
		text


	status_element.classList.remove(
		'connected',
		'connecting',
		'disconnected',
		'error'
	)


	status_element.classList.add(
		status
	)
}


function clear_activity_empty_state() {
	const empty_state =
		document.getElementById(
			'activity-empty-state'
		)

	if (empty_state) {
		empty_state.remove()
	}
}


function get_activity_type_label(
	event_type
) {
	const labels = {
		push: 'Push',
		pull_request: 'Pull request',
		pull_request_review: 'PR review',
		issues: 'Issue',
		issue_comment: 'Issue comment',
		fork: 'Fork'
	}

	return labels[event_type] ||
		String(
			event_type ||
			'Activity'
		)
}


function append_activity_event(
	event_data
) {
	if (!event_data) {
		return
	}


	clear_activity_empty_state()


	const event_element =
		document.createElement(
			'article'
		)

	event_element.classList.add(
		'activity-event'
	)


	const type_element =
		document.createElement(
			'span'
		)

	type_element.classList.add(
		'activity-event-type'
	)

	type_element.textContent =
		get_activity_type_label(
			event_data.event_type
		)


	const message_element =
		document.createElement(
			'p'
		)

	message_element.classList.add(
		'activity-event-message'
	)

	message_element.textContent =
		event_data.message ||
		'GitHub activity received.'


	event_element.appendChild(
		type_element
	)

	event_element.appendChild(
		message_element
	)


	if (event_data.url) {
		const link_element =
			document.createElement(
				'a'
			)

		link_element.classList.add(
			'activity-event-link'
		)

		link_element.href =
			event_data.url

		link_element.target =
			'_blank'

		link_element.rel =
			'noopener noreferrer'

		link_element.textContent =
			'View on GitHub'


		event_element.appendChild(
			link_element
		)
	}


	const feed =
		document.getElementById(
			'activity-feed'
		)

	feed.prepend(
		event_element
	)
}


function start_activity_stream() {
	if (activity_source) {
		activity_source.close()
	}


	set_activity_connection_status(
		'connecting',
		'Connecting...'
	)


	activity_source =
		new EventSource(
			`${BACKEND_URL}/live-feed/${encodeURIComponent(repository_id)}`,
			{
				withCredentials: true
			}
		)


	activity_source.onopen =
		function () {
			set_activity_connection_status(
				'connected',
				'Live'
			)
		}


	activity_source.onmessage =
		function (event) {
			try {
				const event_data =
					JSON.parse(
						event.data
					)

				append_activity_event(
					event_data
				)
			}
			catch (error) {
				console.error(
					'Failed to parse live activity event:',
					error
				)
			}
		}


	activity_source.onerror =
		function () {
			set_activity_connection_status(
				'disconnected',
				'Disconnected'
			)
		}
}


function close_activity_stream() {
	if (!activity_source) {
		return
	}

	activity_source.close()
	activity_source = null
}


/* ------------------------------------------------------------ */
/* Event handlers                                                 */
/* ------------------------------------------------------------ */

function initialize_event_handlers() {
	const reload_overview_button =
		document.getElementById(
			'reload-overview-button'
		)

	const retry_overview_button =
		document.getElementById(
			'retry-overview-button'
		)

	const reload_health_button =
		document.getElementById(
			'reload-health-button'
		)

	const retry_health_button =
		document.getElementById(
			'retry-health-button'
		)

	const retry_activity_graph_button =
		document.getElementById(
			'retry-activity-graph-button'
		)


	if (reload_overview_button) {
		reload_overview_button.addEventListener(
			'click',
			load_overview
		)
	}


	if (retry_overview_button) {
		retry_overview_button.addEventListener(
			'click',
			load_overview
		)
	}


	if (reload_health_button) {
		reload_health_button.addEventListener(
			'click',
			function () {
				health_metrics_loaded = false
				activity_graph_loaded = false

				load_health_metrics()
				load_activity_graph()
			}
		)
	}


	if (retry_health_button) {
		retry_health_button.addEventListener(
			'click',
			load_health_metrics
		)
	}


	if (retry_activity_graph_button) {
		retry_activity_graph_button.addEventListener(
			'click',
			load_activity_graph
		)
	}


	window.addEventListener(
		'pagehide',
		close_activity_stream
	)

	window.addEventListener(
		'beforeunload',
		close_activity_stream
	)
}


/* ------------------------------------------------------------ */
/* Initialization                                                 */
/* ------------------------------------------------------------ */

async function initialize_repository_page() {
	initialize_tabs()
	initialize_event_handlers()

	await load_repository_information()

	await load_overview()

	start_activity_stream()
}


initialize_repository_page().catch(
	error => {
		console.error(
			'Failed to initialize repository page:',
			error
		)
	}
)