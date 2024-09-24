window.app.component('schedule-details', {
  name: 'schedule-details',
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
          this.unavailableDatesBlocks = res.data
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
    this.events = this.appointments.map(appointment => {
      return appointment.start_time.split(' ')[0]
    })
    this.getUnavailableDates()
    this.availableDays = this.schedule.available_days
  },
  template: `
    <q-card
      class="q-pa-lg q-pt-xl lnbits__dialog-card"
      style="min-height: 60vh; width: 700px; max-width: 80vw"
    >
      <q-tabs v-model="tab" no-caps align="justify">
        <q-tab name="info" label="Schedule Info"></q-tab>
        <q-tab name="edit_unavailable" label="Unavailable Dates"></q-tab>
        <q-tab name="unavailable" label="Set Unavailable"></q-tab>
      </q-tabs>
      <q-card-section style="min-height: 50vh" class="scroll">
        <q-tab-panels v-model="tab">
          <q-tab-panel name="info">
            <q-splitter v-model="splitterModel">
              <template v-slot:before>
                <div class="q-pa-md">
                  <q-date
                    v-model="date"
                    :events="events"
                    event-color="primary"
                    :options="availableDaysFn"
                    today-btn
                  ></q-date>
                </div>
              </template>
              <template v-slot:after>
                <div class="q-pa-md" v-if="eventsByDate.length">
                  <q-list bordered>
                    <q-expansion-item
                      v-for="event in eventsByDate"
                      :key="event.id"
                      group="events"
                      expand-separator
                      icon="event"
                      :label="event.name"
                      :caption="timeFormatted(event).time"
                    >
                      <q-card>
                        <q-card-section class="text-caption">
                          <p v-text="event.info || 'No description'"></p>
                          <p class="q-mt-lg" v-text="timeFormatted(event).fromNow"></p>
                          <p v-if="event.email" v-text="'Contact: '+event.email"></p>
                        </q-card-section>
                      </q-card>
                    </q-expansion-item>
                  </q-list>
                </div>
                <div v-else class="q-pa-md">
                  <p class="text-h5">No appointments</p>
                </div>
              </template>
            </q-splitter>
          </q-tab-panel>
          <q-tab-panel name="unavailable">
            <p class="h6">Select days off</p>
            <div class="q-pa-md">
              <q-date
                v-model="dateRange"
                landscape
                range
                today-btn
                :events="events"
                :options="availableDaysFn"
              ></q-date>
              <div class="q-mt-lg">
                <p>
                  <span v-if="dateRange" v-text="'Set unavailable from '+dateRange.from+' to '+dateRange.to"></span>
                  <span v-else>Select a date range to be unavailable</span>
                </p>
                <q-btn
                  align="right"
                  color="primary"
                  label="Set Unavailable"
                  @click="setUnavailableDates"
                  :disable="!dateRange"
                ></q-btn>
              </div>
            </div>
          </q-tab-panel>
          <q-tab-panel name="edit_unavailable">
            <p class="h6">Select days off</p>
            <div class="q-pa-md">
              <q-table
                title="Availability"
                :rows="unavailableDatesBlocks"
                :columns="unavailableTable.columns"
                row-key="id"
                selection="single"
                :selected.sync="selectedBlock"
                :pagination.sync="unavailableTable.pagination"
              ></q-table>
              <div class="q-mt-lg">
                <q-btn
                  align="right"
                  color="primary"
                  label="Delete Selected"
                  @click="deleteUnavailableDate"
                  :disable="!selectedBlock.length"
                ></q-btn>
              </div>
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat label="Close" v-close-popup />
      </q-card-actions>
    </q-card>
  `
})
