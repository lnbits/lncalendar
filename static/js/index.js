window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  computed: {
    endpoint: function () {
      return `/lncalendar/api/v1/settings?usr=${this.g.user.id}`
    }
  },
  data: function () {
    return {
      settings: [
        {
          type: 'str',
          description: 'Nostr private key used for notifications',
          name: 'nostr_private_key'
        },
        {
          type: 'str',
          description: 'Comma seperated list of relays',
          name: 'relays'
        },
      ],
      schedules: [],
      schedulesTable: {
        columns: [
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
          {name: 'name', align: 'left', label: 'Name', field: 'name'},
          {
            name: 'amount',
            align: 'right',
            label: 'Amount (sat)',
            field: 'amount',
            sortable: true,
            sort: function (a, b, rowA, rowB) {
              return rowA.amount - rowB.amount
            }
          },
          {
            name: 'starts',
            align: 'left',
            label: 'Starts',
            field: 'start_day',
            format: (val, row) =>
              `${_.findWhere(this.weekdays, {value: val}).label} @ ${
                row.start_time
              }`
          },
          {
            name: 'ens',
            align: 'left',
            label: 'Ends',
            field: 'end_day',
            format: (val, row) =>
              `${_.findWhere(this.weekdays, {value: val}).label} @ ${
                row.end_time
              }`
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      appointments: [],
      appointmentsTable: {
        columns: [
          {
            name: 'id',
            align: 'left',
            label: 'ID',
            field: 'id'
          },
          {
            name: 'paid',
            align: 'left',
            label: 'Paid',
            field: 'paid'
          },
          {
            name: 'name',
            align: 'left',
            label: 'Name',
            field: 'name'
          },
          {
            name: 'date',
            align: 'left',
            label: 'Date',
            field: 'date'
          },
          {
            name: 'time',
            align: 'left',
            label: 'Time',
            field: 'time'
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      weekdays: [
        {label: 'Monday', value: 0},
        {label: 'Tuesday', value: 1},
        {label: 'Wednesday', value: 2},
        {label: 'Thursday', value: 3},
        {label: 'Friday', value: 4},
        {label: 'Saturday', value: 5},
        {label: 'Sunday', value: 6}
      ],
      formDialog: {
        show: false,
        show_start_time: false,
        show_end_time: false,
        timeFormat24: true,
        data: {}
      },
      scheduleDialog: {
        show: false,
        data: {}
      }
    }
  },
  methods: {
    getSchedules() {
      LNbits.api
        .request(
          'GET',
          '/lncalendar/api/v1/schedule?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.schedules = response.data.map(mapSchedule)
        })
    },
    resetForm() {
      this.formDialog.data = {}
    },
    sendFormData() {
      const data = {...this.formDialog.data}
      const wallet = _.findWhere(this.g.user.wallets, {id: data.wallet})
      if (data.id) {
        this.updateSchedule(wallet, data)
      } else {
        this.createSchedule(wallet, data)
      }
      this.formDialog.show = false
      this.resetForm()
    },
    async createSchedule(wallet, data) {
      try {
        let response = await LNbits.api.request(
          'POST',
          '/lncalendar/api/v1/schedule',
          wallet.adminkey,
          data
        )
        this.getSchedules()
        this.$q.notify({
          type: 'positive',
          message: 'New schedule created',
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    updateDialog(scheduleId) {
      this.formDialog.data = this.schedules.find(
        schedule => schedule.id == scheduleId
      )
      this.formDialog.show = true
    },
    async updateSchedule(wallet, data) {
      try {
        let response = await LNbits.api.request(
          'PUT',
          '/lncalendar/api/v1/schedule/' + data.id,
          wallet.inkey,
          data
        )
        const index = _.findIndex(this.schedules, {id: data.id})
        this.schedules.splice(index, 1, mapSchedule(response.data))
        Quasar.Notify.create({
          type: 'positive',
          message: 'Schedule Updated',
          timeout: 5000
        })
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    deleteSchedule(scheduleId) {
      LNbits.utils
        .confirmDialog(
          'All data will be lost! Are you sure you want to delete this schedule?'
        )
        .onOk(async () => {
          try {
            const schedule = _.findWhere(this.schedules, {id: scheduleId})
            const wallet = _.findWhere(this.g.user.wallets, {
              id: schedule.wallet
            })
            await LNbits.api.request(
              'DELETE',
              '/lncalendar/api/v1/schedule/' + scheduleId,
              wallet.adminkey
            )
            this.$q.notify({
              type: 'positive',
              message: 'Schedule Deleted',
              timeout: 5000
            })
            this.schedules = this.schedules.filter(
              schedule => schedule.id !== scheduleId
            )
          } catch (error) {
            console.warn(error)
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    scheduleDialogFn(schedule) {
      if (this.scheduleDialog.show == true) {
        this.scheduleDialog.show = false
        this.scheduleDialog.data = {}
      } else {
        this.scheduleDialog.show = true
        this.scheduleDialog.data = schedule
      }
    },
    async getAppointments() {
      try {
        let appointments = await LNbits.api.request(
          'GET',
          '/lncalendar/api/v1/appointment',
          this.g.user.wallets[0].inkey
        )
        this.appointments = appointments.data.map(mapAppointment)
      } catch (error) {
        console.warn(error)
        LNbits.utils.notifyApiError(error)
      }
    },
    exportCSV() {
      LNbits.utils.exportCSV(this.schedulesTable.columns, this.schedules)
    }
  },
  created() {
    if (this.g.user.wallets.length) {
      this.getSchedules()
      this.getAppointments()

      // check if time format is 24h
      this.formDialog.timeFormat24 = !new Intl.DateTimeFormat([], {
        hour: 'numeric'
      })
        .format(0)
        .match(/\s/)
    }
  }
})
