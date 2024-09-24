window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  data: function () {
    return {
      date: null,
      timeSlot: null,
      appointments: [],
      unavailableDates: new Set(),
      formDialog: {
        data: {
          name: '',
          email: '',
          text: ''
        }
      },
      paymentDialog: {
        show: false,
        paymentRequest: null,
        paymentHash: null,
        dismissMsg: () => {},
        paymentChecker: null
      }
    }
  },
  computed: {
    timeSlots() {
      const [startHour, startMinute] = this.schedule.start_time
        .split(':')
        .map(Number)
      const [endHour, endMinute] = this.schedule.end_time.split(':').map(Number)
      const slots = []

      for (
        let time = startHour * 60 + startMinute;
        time <= endHour * 60 + endMinute;
        time += 30
      ) {
        const hour = Math.floor(time / 60)
        const minute = time % 60
        slots.push(
          `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
        )
      }
      return slots
    },
    appointmentDate() {
      if (!this.date || !this.timeSlot) return ''
      let formattedDate = Quasar.date.formatDate(
        new Date(this.date),
        'ddd, Do MMM, YYYY'
      )
      return `Appointment at ${this.timeSlot} on ${formattedDate}`
    },
    timePassed() {
      return new Date(this.date).valueOf() != this.today.valueOf()
    }
  },
  methods: {
    availableDaysFn(date) {
      if (this.unavailableDatesFn(date)) return false
      if (new Date(date) < this.today) return false
      let weekday = new Date(date).getDay() - 1
      return this.availableDays.some(d => d === weekday)
    },
    bookAppointment(time) {
      this.timeSlot = time
      return
    },
    isBooked(time) {
      return this.appointments
        .filter(ap => ap.date === this.date)
        .some(appointment => appointment.start_time.split(' ')[1] === time)
    },
    timePassedFn(time) {
      if (this.isBooked(time)) return true
      if (this.timePassed) return false
      const [hour, minute] = time.split(':').map(Number)
      const now = new Date()
      return (
        now.getHours() > hour ||
        (now.getHours() === hour && now.getMinutes() > minute)
      )
    },
    unavailableDatesFn(date) {
      return this.unavailableDates.has(date)
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
          console.error(err)
        })
    },
    async purgeAppointments() {
      try {
        await LNbits.api.request(
          'GET',
          `/lncalendar/api/v1/appointment/purge/${this.schedule.id}`
        )
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    async getAppointments() {
      try {
        let appointments = await LNbits.api.request(
          'GET',
          `/lncalendar/api/v1/appointment/${this.schedule.id}`
        )
        this.appointments = appointments.data.map(mapAppointment)
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    createAppointment() {
      LNbits.api
        .request('POST', '/lncalendar/api/v1/appointment', null, {
          name: this.formDialog.data.name,
          email: this.formDialog.data.email,
          info: this.formDialog.data.text,
          start_time: `${this.date} ${this.timeSlot}`,
          end_time: `${this.date} ${add30min(this.timeSlot)}`,
          schedule: this.schedule.id
        })
        .then(response => {
          this.paymentDialog.paymentRequest = response.data.payment_request
          this.paymentDialog.paymentHash = response.data.payment_hash
          this.openPaymentDialog()
        })
        .catch(error => {
          LNbits.utils.notifyApiError(error)
        })
    },
    openPaymentDialog() {
      this.paymentDialog.show = true
      this.formDialog.dismissMsg = this.$q.notify({
        timeout: 0,
        message: 'Waiting for payment...'
      })
      this.paymentDialog.paymentChecker = setInterval(() => {
        LNbits.api
          .request(
            'GET',
            `/lncalendar/api/v1/appointment/${this.schedule.id}/${this.paymentDialog.paymentHash}`
          )
          .then(async response => {
            if (response.data.paid) {
              this.closePaymentDialog()
              await this.getAppointments()
            }
          })
          .catch(error => {
            LNbits.utils.notifyApiError(error)
          })
      }, 3000)
    },
    async closePaymentDialog() {
      clearInterval(this.paymentDialog.paymentChecker)
      this.formDialog.dismissMsg()
      this.resetPaymentDialog()
      this.resetData()
      this.$q.notify({
        type: 'positive',
        message: 'Sats received, thanks!',
        icon: 'thumb_up'
      })
    },
    resetData() {
      this.formDialog.data.name = ''
      this.formDialog.data.email = ''
      this.formDialog.data.text = ''
      this.date = Quasar.date.formatDate(Date.now(), 'YYYY/MM/DD')
      this.timeSlot = null
    },
    resetPaymentDialog() {
      this.paymentDialog = {
        show: false,
        paymentRequest: null,
        paymentHash: null,
        dismissMsg: () => {},
        paymentChecker: null
      }
    }
  },
  async created() {
    this.schedule = schedule
    this.availableDays = availableDays
    this.date = Quasar.date.formatDate(Date.now(), 'YYYY/MM/DD')
    this.today = new Date(this.date)
    await this.purgeAppointments()
    await this.getAppointments()
    this.getUnavailableDates()
  }
})
