const is_production = window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"

let BACKEND_URL

if (is_production) {
	// production backend URL, set once repo-signals is actually deployed
	BACKEND_URL = ""
}
else {
	// local development backend URL
	BACKEND_URL = "http://localhost:8000"
}

export { BACKEND_URL }