import http from 'k6/http'
import {check} from 'k6'

const payloadTemplate = JSON.parse(open('./payload.json'))

export const options = {
    scenarios: {
        crash_test: {
            executor: 'constant-arrival-rate',
            rate: 2,
            timeUnit: '1s',
            duration: '10s',
            preAllocatedVUs: 20,
            maxVUs: 50,
        }
    }
}

export default function () {
    const uniqueId = `loadtest-${__VU}-${__ITER}-${Date.now()}`
    const body = { ...payloadTemplate, k6_test_id: uniqueId }

    const response = http.post('http://localhost:8000/webhook-payload', JSON.stringify(body), {
        headers: {
          'Content-Type': 'application/json', 
          'X-GitHub-Event': 'push',
          'X-GitHub-Delivery': uniqueId 
        },
    })
  check(response, { 'is ok': (r) => r.status === 200 })
}