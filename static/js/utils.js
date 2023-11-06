const mapSchedule = obj => {
  obj.displayUrl = `/lncalendar/${obj.id}`
  return obj
}

const mapAppointment = obj => {
  let [date, time] = obj.start_time.split(' ')
  obj.date = Quasar.utils.date.formatDate(date, 'YYYY/MM/DD')
  obj.time = time
  return obj
}

const extractUnavailableDates = arr => {
  const unavailableSet = new Set()
  arr.forEach(obj => {
    const startDate = new Date(obj.start_time)
    const endDate = new Date(obj.end_time)

    for (
      let date = new Date(startDate);
      date <= endDate;
      date.setDate(date.getDate() + 1)
    ) {
      unavailableSet.add(Quasar.utils.date.formatDate(date, 'YYYY/MM/DD'))
    }
  })
  return unavailableSet
}

const add30min = time => {
  const [hours, minutes] = time.split(':').map(Number)
  let newHours = hours
  let newMinutes = minutes + 30

  if (newMinutes >= 60) {
    newHours = (newHours + 1) % 24 // To handle the case where hours can go over 24
    newMinutes -= 60
  }

  const newTime = `${String(newHours).padStart(2, '0')}:${String(
    newMinutes
  ).padStart(2, '0')}`
  return newTime
}

function loadTemplateAsync(path) {
  const result = new Promise(resolve => {
    const xhttp = new XMLHttpRequest()

    xhttp.onreadystatechange = function () {
      if (this.readyState == 4) {
        if (this.status == 200) resolve(this.responseText)

        if (this.status == 404) resolve(`<div>Page not found: ${path}</div>`)
      }
    }

    xhttp.open('GET', path, true)
    xhttp.send()
  })

  return result
}
