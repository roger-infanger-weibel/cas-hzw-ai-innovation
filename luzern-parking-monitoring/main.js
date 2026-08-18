import { renderParkingMarkers } from './parkingMarkers.js'
import { renderNavigation } from './parkingNavigation.js'
import { isIOS, mobileMQ } from './browser.js'
import { getParkingApiData } from './parkingApiData.js'
import { mapCircles } from './mapCircles.js'

jQuery(function () {
  const map = initializeMap()
  if (!map) {
    return
  }
  mapCircles(map)
  initAllViews()
  updateParkingsFromApi()

  setTimeout(
    () => {window.location.reload()},
    300000 // 5 minutes
  )

  jQuery('#list-container').on('click', '.region-title', function () {
    jQuery('#list-container .region-title').removeClass('open')
    jQuery(this).parent().parent().find('ul').hide()
    jQuery(this).addClass('open')
    jQuery(this).parent().find('ul').show()
  })
  jQuery('#show-map').on('click', function () {
    jQuery(this).addClass('active')
    jQuery('#show-list').removeClass('active')
    showMap()
  })
  jQuery('#show-list').on('click', function () {
    jQuery(this).addClass('active')
    jQuery('#show-map').removeClass('active')
    showList()
  })
  if (matchMedia && mobileMQ.addListener) {
    mobileMQ.addListener(isMobile)
    isMobile(mobileMQ)
  }

  function isMobile(mq) {
    if (mq.matches) {
      jQuery('#list-container').on('click', '.parking-station', function () {
        showMap()
      })
    }
  }

  function showMap() {
    jQuery('#site-container').hide()
    jQuery('#map-container').show()
  }

  function showList() {
    jQuery('#map-container').hide()
    jQuery('#site-container').show()
  }

  function initializeMap() {
    const mapElement = document.getElementById('map-canvas')
    if (!mapElement) {
      return undefined
    }
    const mapOptions = getMapOptions()
    const map = new google.maps.Map(
      document.getElementById('map-canvas'),
      mapOptions
    )
    return map
  }

  function initAllViews() {
    if (isIOS) {
      jQuery('body').find('.has-hover').removeClass('has-hover')
    }
    jQuery('header nav').naver({
      customClass: 'main-navigation',
      labels: { closed: '&#xf0c9;', open: '&#xf00d;' },
      maxWidth: '767px',
    })
  }

  function updateParkingsFromApi() {
    getParkingApiData().then(data => {
      jQuery('#list-container').html(renderNavigation(data))
      renderParkingMarkers(map, data)
    })
  }

  function getMapOptions() {
    const mapOptions = {
      center: new google.maps.LatLng(47.051386, 8.303741),
      disableDefaultUI: false,
      // mapId: "pls", // Map ID is required for advanced markers.
      panControl: false,
      zoom: 15,
      zoomControl: true,
      zoomControlOptions: {
        position: google.maps.ControlPosition.LEFT_CENTER,
      },
      styles: [
        { featureType: 'landscape', stylers: [{ color: '#f0ede5' }] },
        {
          featureType: 'road.local',
          elementType: 'geometry',
          stylers: [{ visibility: 'simplified' }, { color: '#f5f5f5' }],
        },
        { featureType: 'water', stylers: [{ weight: 0.4 }] },
        { featureType: 'poi', stylers: [{ visibility: 'off' }] },
        {
          featureType: 'road.arterial',
          elementType: 'geometry.stroke',
          stylers: [{ visibility: 'on' }, { color: '#bfbfbf' }],
        },
        {
          featureType: 'road.arterial',
          elementType: 'geometry.fill',
          stylers: [{ visibility: 'on' }, { color: '#f8f8f8' }],
        },
        {
          featureType: 'water',
          stylers: [
            { visibility: 'on' },
            { saturation: -13 },
            { lightness: 25 },
            { gamma: 1.05 },
          ],
        },
        {
          featureType: 'road.highway',
          elementType: 'geometry.fill',
          stylers: [{ visibility: 'on' }, { lightness: 25 }],
        },
        {
          featureType: 'road.highway.controlled_access',
          stylers: [{ visibility: 'on' }, { weight: 2.3 }, { lightness: 40 }],
        },
        { featureType: 'transit.station', stylers: [{ visibility: 'off' }] },
        {
          featureType: 'road.highway',
          elementType: 'labels',
          stylers: [{ visibility: 'on' }],
        },
        {
          featureType: 'transit.line',
          stylers: [
            { visibility: 'simplified' },
            { color: '#d4d4d4' },
            { weight: 0.4 },
          ],
        },
        {
          featureType: 'road.local',
          elementType: 'labels.text.stroke',
          stylers: [{ visibility: 'on' }, { color: '#ffffff' }],
        },
        {
          featureType: 'road.local',
          elementType: 'labels.text.fill',
          stylers: [{ color: '#9b9b9b' }],
        },
      ],
    }
    return mapOptions
  }
})
