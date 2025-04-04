window.app.component('schedule-details', {
  name: 'schedule-details',
  template: '#schedule-details',
  props: ['schedule', 'appointments', 'wallet'],
  data: function () {
    return {
      tab: 'info',
      date: null,
      dateRange: null,
      events: [],
      splitterModel: 60,
      eventsByDate: [],
      unavailableDates: new Set(),
      unavailableDatesBlocks: [],
      selectedBlock: [],
      unavailableTable: {
        columns: [
          {
            name: 'starts',
            align: 'left',
            label: 'Starts',
            field: 'start_time',
            field: row => row.start_time,
            sortable: true
          },
          {
            name: 'ens',
            align: 'left',
            label: 'Ends',
            field: 'end_time',
            field: row => row.end_time,
            sortable: true
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      }
    }
  },

  computed: {},

  methods: {
    textSetUnavailable(dateRange) {
      const range =
        typeof dateRange === 'string'
          ? dateRange
          : `from ${dateRange.from} to ${dateRange.to}`
      return `Set unavailable ${range}`
    },
    timeFormatted(eventInfo) {
      if (!eventInfo) return null
      let [date, time] = eventInfo.start_time.split(' ')
      let formattedDate = Quasar.date.formatDate(
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
          this.unavailableDatesBlocks = res.data
        })
        .catch(err => {
          console.log(err)
        })
    },
    async setUnavailableDates() {
      const schedule = this.schedule.id
      try {
        // dateRange is a string if only 1 day is selected
        if (typeof this.dateRange === 'string') {
          this.dateRange = {
            from: this.dateRange,
            to: this.dateRange
          }
        }
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
        this.getUnavailableDates()
        this.dateRange = null
        this.$q.notify({
          type: 'positive',
          message: 'Unavailable dates set',
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    async deleteUnavailableDate() {
      const id = this.selectedBlock[0].id
      await LNbits.api
        .request(
          'DELETE',
          `/lncalendar/api/v1/unavailable/${this.schedule.id}/${id}`,
          this.wallet.adminkey
        )
        .then(res => {
          this.selectedBlock = []
          this.getUnavailableDates()
          this.$q.notify({
            type: 'positive',
            message: 'Unavailable date deleted',
            timeout: 3000
          })
        })
        .catch(err => {
          console.log(err)
        })
    }
  },

  created: async function () {
    this.date = Quasar.date.formatDate(Date.now(), 'YYYY/MM/DD')
    this.today = new Date(this.date)
    this.events = this.appointments.map(appointment => {
      return appointment.start_time.split(' ')[0]
    })
    this.getUnavailableDates()
    this.availableDays = this.schedule.available_days
  }
})
