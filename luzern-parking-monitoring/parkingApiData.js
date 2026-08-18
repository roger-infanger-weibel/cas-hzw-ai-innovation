const urlApi = 'https://info.pls-luzern.ch/TeqParkingWS/GetFreeParks'

export function getParkingApiData() {
  return fetch(urlApi).then(response => {
    if (response.status !== 200) {
      console.log(`No data from API:`, response)
      return ''
    }
    return response.json().then(json => json.data)
  })
}
