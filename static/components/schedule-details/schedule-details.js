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
        eventsByDate: [],
        unavailableDates: new Set()
      }
    },

    computed: {},

    methods: {
      timeFormatted(eventInfo) {
        if (!eventInfo) return null
        let [date, time] = eventInfo.start_time.split(' ')
        let formattedDate = Quasar.utils.date.formatDate(
          new Date(date),
          'ddd, Do MMM, YYYY'
        )
        let m = moment(eventInfo.start_time, 'YYYY/MM/DD HH:mm')
        let isPass = m.isBefore(moment())
        console.log(time)
        return {
          date: formattedDate,
          time: moment(time, 'HH:mm').format('hh:mm'),
          fromNow: `${isPass ? '' : 'Starts'} ${m.fromNow()}`
        }
      },
      dateChanged(val) {
        this.eventsByDate = this.appointments
          .filter(appointment => {
            return appointment.start_time.split(' ')[0] == val
          })
          .sort((a, b) => {
            return moment(a.time, 'HH:mm') - moment(b.time, 'HH:mm')
          })
        console.log(this.eventsByDate)
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
            this.unavailableDates = new Set([
              ...this.unavailableDates,
              ...extractUnavailableDates(res.data)
            ])
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
