import http from 'k6/http'
import {check } from 'k6'
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js"

const payload = open('./payload.json')

export const options = {
  scenarios: {
    webhook_to_db: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1s',
      duration: '30s',
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
}

export default function () {
  const response = http.post('http://localhost:8000/webhook-db', payload, 
    {headers: 
      {
        'Content-Type': 'application/json', 
        'X-Github-Event': 'push' 
      },
  })
  check(response, {
    'is ok': (r) => r.status === 200,
  })
}

export function handleSummary(data){
  return {
    "report_db_100rps.html": htmlReport(data)
  }
}