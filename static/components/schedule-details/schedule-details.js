async function scheduleDetails(path) {
  const template = await loadTemplateAsync(path)
  Vue.component('schedule-details', {
    name: 'schedule-details',
    template,
    delimiters: ['${', '}'],
    props: ['schedule', 'appointments', 'wallet'],
    data: function () {
      return {
        tab: 'info',
        date: null,
        dateRange: null,
        events: [],
        splitterModel: 60,
        eventInfo: null,
        unavailableDates: new Set()
      }
    },

    computed: {
      timeFormatted() {
        if (!this.eventInfo) return null
        let [date, time] = this.eventInfo.start_time.split(' ')
        let formattedDate = Quasar.utils.date.formatDate(
          new Date(date),
          'ddd, Do MMM, YYYY'
        )
        let m = moment(this.eventInfo.start_time, 'YYYY/MM/DD HH:mm')
        let isPass = m.isBefore(moment())
        return {
          date: formattedDate,
          time: time,
          fromNow: `${isPass ? 'Started' : 'Starts'} ${m.fromNow()}`
        }
      }
    },

    methods: {
      dateChanged(val) {
        this.eventInfo = this.appointments.find(appointment => {
          return appointment.start_time.split(' ')[0] == val
        })
      },
      availableDaysFn(date) {
        if (new Date(date) < this.today) return false
        let weekday = new Date(date).getDay() - 1
        return (
          this.availableDays.some(d => d === weekday) &&
          this.unavailableDatesFn(date)
        )
      },
      unavailableDatesFn(date) {
        return !this.unavailableDates.has(date)
      },
      getUnavailableDates() {
        LNbits.api
          .request('GET', `/lncalendar/api/v1/unavailable/${this.schedule.id}`)
          .then(res => {
            res.data.forEach(obj => {
              const startDate = new Date(obj.start_time)
              const endDate = new Date(obj.end_time)

              for (
                let date = new Date(startDate);
                date <= endDate;
                date.setDate(date.getDate() + 1)
              ) {
                this.unavailableDates.add(
                  Quasar.utils.date.formatDate(date, 'YYYY/MM/DD')
                )
              }
            })
          })
          .catch(err => {
            console.log(err)
          })
      },
      async setUnavailableDates() {
        const schedule = this.schedule.id
        try {
          const unavailable = await LNbits.api.request(
            'POST',
            `/lncalendar/api/v1/unavailable`,
            this.wallet.adminkey,
            {
              start_time: this.dateRange.from,
              end_time: this.dateRange.to,
              schedule
            }
          )

          this.unavailableDates.add(unavailable.data.start_time)
          console.log(this.unavailableDates)
          this.$q.notify({
            type: 'positive',
            message: 'Unavailable dates set',
            timeout: 5000
          })
        } catch (error) {
          console.warn(error)
          LNbits.utils.notifyApiError(error)
        }
      }
    },

    created: async function () {
      this.events = this.appointments.map(appointment => {
        return appointment.start_time.split(' ')[0]
      })
      this.getUnavailableDates()
      this.availableDays = this.schedule.available_days
    }
  })
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
