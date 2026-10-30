<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  ApiError,
  getAssociation,
  getPlanningPeriod,
  getSchedule,
  register,
  setRegistrationStatus,
  type Association,
  type Member,
  type OccurrenceRegistration,
  type PlanningPeriod,
  type Schedule,
} from '../api'
import {
  addDays,
  formatDate,
  isoWeek,
  longDay,
  minutes,
  mondayOf,
  shortClock,
  shortDay,
  today,
  weekdayIndex,
} from '../dates'
import { useSession } from '../session'

const FIRST_WEEKS = 6
const MORE_WEEKS = 4

/** An occurrence, or an obsolete registration placed like one. */
interface Item {
  key: string
  date: string
  start: string
  end: string
  registration: OccurrenceRegistration | null
  obsolete: boolean
  lane: number
  lanes: number
}

const props = defineProps<{ id: string }>()
const { t, locale } = useI18n()
const { user } = useSession()

const day0 = today()
const firstMonday = addDays(mondayOf(day0), -7)
const weeks = ref(FIRST_WEEKS)
const association = ref<Association>()
const schedule = ref<Schedule>({ occurrences: [], obsolete: [], closures: [] })
const period = ref<PlanningPeriod | null>(null)
const openKey = ref<string>()
const asking = ref(false)
const menuPosition = ref({ left: 0, top: 0 })
const menu = ref<HTMLElement>()
const message = ref<string>()

const lastDay = computed(() => addDays(firstMonday, 7 * weeks.value - 1))
const isManager = computed(() => association.value?.role === 'manager')
const members = computed(() =>
  [...(association.value?.members ?? [])].sort((a, b) =>
    a.display_name.localeCompare(b.display_name),
  ),
)

async function load() {
  ;[association.value, schedule.value, period.value] = await Promise.all([
    getAssociation(props.id),
    getSchedule(props.id, firstMonday, lastDay.value),
    getPlanningPeriod(props.id),
  ])
}

async function reload() {
  schedule.value = await getSchedule(props.id, firstMonday, lastDay.value)
}

async function more() {
  const from = addDays(lastDay.value, 1)
  const added = await getSchedule(props.id, from, addDays(from, 7 * MORE_WEEKS - 1))
  const known = new Set(schedule.value.closures.map((c) => c.id))
  schedule.value = {
    occurrences: [...schedule.value.occurrences, ...added.occurrences],
    obsolete: [...schedule.value.obsolete, ...added.obsolete],
    closures: [...schedule.value.closures, ...added.closures.filter((c) => !known.has(c.id))],
  }
  weeks.value += MORE_WEEKS
}

watch(() => props.id, load, { immediate: true })

/** Each day's items, with lanes so that overlapping ones sit side by side. */
const itemsByDate = computed(() => {
  const byDate = new Map<string, Item[]>()
  const push = (item: Omit<Item, 'key' | 'lane' | 'lanes'>) => {
    const list = byDate.get(item.date) ?? []
    list.push({ ...item, key: `${item.date} ${item.start} ${item.end}`, lane: 0, lanes: 1 })
    byDate.set(item.date, list)
  }
  for (const o of schedule.value.occurrences) push({ ...o, obsolete: false })
  for (const r of schedule.value.obsolete) {
    const { date, start, end, ...registration } = r
    push({ date, start, end, registration, obsolete: true })
  }
  for (const list of byDate.values()) {
    list.sort((a, b) => minutes(a.start) - minutes(b.start))
    // Items that overlap, directly or through others, share their lanes.
    let cluster: Item[] = []
    let clusterEnd = 0
    const laneEnds: number[] = []
    const closeCluster = () => {
      for (const item of cluster) item.lanes = laneEnds.length
      cluster = []
      laneEnds.length = 0
    }
    for (const item of list) {
      if (minutes(item.start) >= clusterEnd) closeCluster()
      let lane = laneEnds.findIndex((laneEnd) => laneEnd <= minutes(item.start))
      if (lane < 0) lane = laneEnds.push(0) - 1
      laneEnds[lane] = minutes(item.end)
      item.lane = lane
      cluster.push(item)
      clusterEnd = Math.max(clusterEnd, minutes(item.end))
    }
    closeCluster()
  }
  return byDate
})

// Obsolete registrations count too, so that each finds a column and fits the time scale.
const allItems = computed(() => [...itemsByDate.value.values()].flat())
const columns = computed(() =>
  [...new Set(allItems.value.map((i) => weekdayIndex(i.date)))].sort((a, b) => a - b),
)
const firstHour = computed(() =>
  Math.floor(Math.min(...allItems.value.map((i) => minutes(i.start))) / 60),
)
const lastHour = computed(() =>
  Math.ceil(Math.max(...allItems.value.map((i) => minutes(i.end))) / 60),
)
const hours = computed(() => lastHour.value - firstHour.value)

const shownWeeks = computed(() =>
  Array.from({ length: weeks.value }, (_, n) => {
    const monday = addDays(firstMonday, 7 * n)
    return {
      monday,
      current: monday === mondayOf(day0),
      periodStarts: period.value !== null && mondayOf(period.value.first) === monday,
      periodEnds: period.value !== null && mondayOf(period.value.last) === monday,
      days: columns.value.map((column) => {
        const date = addDays(monday, column)
        const items = itemsByDate.value.get(date) ?? []
        return {
          date,
          items,
          lanes: Math.max(1, ...items.map((i) => i.lanes)),
          closure: schedule.value.closures.find((c) => c.first <= date && date <= c.last),
        }
      }),
    }
  }),
)

function dayLabel(date: string) {
  return formatDate(date, locale.value, shortDay)
}

function weekTitle(monday: string) {
  const dayMonth = { day: 'numeric', month: 'short' } as const
  const range = `${formatDate(monday, locale.value, dayMonth)} – ${formatDate(addDays(monday, 6), locale.value, dayMonth)}`
  return t('schedule.week', { n: isoWeek(monday), range })
}

function times(item: Item) {
  return `${shortClock(item.start)}–${shortClock(item.end)}`
}

function position(item: Item) {
  const span = hours.value * 60
  return {
    '--s': (minutes(item.start) - firstHour.value * 60) / span,
    '--e': (minutes(item.end) - firstHour.value * 60) / span,
    '--lane': item.lane,
    '--lanes': item.lanes,
  }
}

function state(item: Item) {
  return item.registration?.status ?? 'free'
}

function actions(item: Item) {
  const r = item.registration
  const live = r !== null && r.status !== 'cancelled'
  const mine = live && r.user_id === user.value?.id
  return {
    signUp: !live && !item.obsolete,
    propose: !live && !item.obsolete && isManager.value,
    confirm: live && (mine || isManager.value) && r.status === 'proposed' && !item.obsolete,
    cancel: live && (mine || isManager.value),
  }
}

function clickable(item: Item) {
  return item.date >= day0 && Object.values(actions(item)).some(Boolean)
}

const openItem = computed(() => allItems.value.find((i) => i.key === openKey.value))
const openActions = computed(() => (openItem.value ? actions(openItem.value) : undefined))

function toggle(item: Item, event: MouseEvent) {
  asking.value = false
  if (openKey.value === item.key) {
    openKey.value = undefined
    return
  }
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  menuPosition.value = { left: rect.right + 8, top: rect.top }
  openKey.value = item.key
  nextTick(() => placeMenu(rect))
}

/** Beside the item, on its right if it fits, else on its left; always inside the window. */
function placeMenu(rect: DOMRect) {
  const width = menu.value?.offsetWidth ?? 0
  const height = menu.value?.offsetHeight ?? 0
  const margin = 16
  let left = rect.right + 8
  if (left + width > window.innerWidth - margin) left = rect.left - width - 8
  menuPosition.value = {
    left: Math.max(margin, Math.min(left, window.innerWidth - width - margin)),
    top: Math.max(margin, Math.min(rect.top, window.innerHeight - height - margin)),
  }
}

function close() {
  openKey.value = undefined
  asking.value = false
}

onMounted(() => document.addEventListener('click', close))
onBeforeUnmount(() => document.removeEventListener('click', close))

async function act(run: () => Promise<unknown>) {
  message.value = undefined
  try {
    await run()
  } catch (e) {
    message.value = e instanceof ApiError && e.status === 409 ? t('schedule.taken') : t('error')
  }
  close()
  await reload()
}

function signUp(item: Item) {
  return act(() => register(props.id, user.value!.id, item.date, item.start, item.end))
}

function propose(item: Item, member: Member) {
  return act(() => register(props.id, member.user_id, item.date, item.start, item.end))
}

function setStatus(item: Item, status: 'confirmed' | 'cancelled') {
  return act(() => setRegistrationStatus(props.id, item.registration!.id, status))
}
</script>

<template>
  <template v-if="association">
    <p class="hint">
      <RouterLink :to="`/associations/${id}`">← {{ association.name }}</RouterLink>
    </p>
    <h1>{{ t('schedule.title') }}</h1>
    <p v-if="message" class="error">{{ message }}</p>
    <p v-if="!allItems.length" class="hint">{{ t('schedule.empty') }}</p>

    <div class="weeks">
      <template v-for="week in shownWeeks" :key="week.monday">
        <p v-if="week.current" class="line">
          {{ t('schedule.today', { date: formatDate(day0, locale, longDay) }) }}
        </p>
        <p v-if="period && week.periodStarts" class="line period">
          {{ t('schedule.periodStart', { date: formatDate(period.first, locale, longDay) }) }}
        </p>
        <section class="week">
          <h2>{{ weekTitle(week.monday) }}</h2>
          <div
            v-if="columns.length"
            class="days"
            :style="{ '--hours': hours, '--columns': columns.length }"
          >
            <div class="day axis" aria-hidden="true">
              <div class="day-head"></div>
              <div class="track">
                <span
                  v-for="n in hours + 1"
                  :key="n"
                  :class="['tick', { minor: hours > 6 && n % 2 === 0 }]"
                  :style="{ '--p': (n - 1) / hours }"
                  >{{ t('schedule.hour', { h: firstHour + n - 1 }) }}</span
                >
              </div>
            </div>
            <div
              v-for="day in week.days"
              :key="day.date"
              role="group"
              :aria-label="dayLabel(day.date)"
              :class="['day', { past: day.date < day0, after: period && day.date > period.last }]"
            >
              <div class="day-head">{{ dayLabel(day.date) }}</div>
              <div class="track" :style="{ '--day-lanes': day.lanes }">
                <div v-if="day.closure" class="closure">
                  <strong>{{ t('schedule.closed') }}</strong>
                  <span v-if="day.closure.label">{{ day.closure.label }}</span>
                </div>
                <ul>
                  <li
                    v-for="item in day.items"
                    :key="item.key"
                    :class="[
                      'occ',
                      state(item),
                      { obsolete: item.obsolete, open: item.key === openKey },
                    ]"
                    :style="position(item)"
                  >
                    <component
                      :is="clickable(item) ? 'button' : 'div'"
                      :type="clickable(item) ? 'button' : undefined"
                      class="occ-body"
                      @click.stop="clickable(item) && toggle(item, $event)"
                    >
                      <span class="times">{{ times(item) }}</span>
                      <span v-if="item.registration" class="name">
                        <s v-if="item.registration.status === 'cancelled'">{{
                          item.registration.display_name
                        }}</s>
                        <template v-else
                          >{{ item.registration.display_name
                          }}<template v-if="item.registration.status === 'proposed'">
                            ?</template
                          ></template
                        >
                      </span>
                      <span v-if="item.obsolete" class="tag">{{ t('schedule.obsolete') }}</span>
                    </component>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </section>
        <p v-if="period && week.periodEnds" class="line period">
          {{ t('schedule.periodEnd', { date: formatDate(period.last, locale, longDay) }) }}
        </p>
      </template>
    </div>
    <button type="button" class="more" @click="more">{{ t('schedule.more') }}</button>

    <div
      v-if="openItem && openActions"
      ref="menu"
      class="menu"
      role="dialog"
      :aria-label="`${dayLabel(openItem.date)} ${times(openItem)}`"
      :style="{ left: `${menuPosition.left}px`, top: `${menuPosition.top}px` }"
      @click.stop
    >
      <p class="menu-title">{{ dayLabel(openItem.date) }} · {{ times(openItem) }}</p>
      <template v-if="asking">
        <p>{{ t('schedule.askCancel') }}</p>
        <div class="actions">
          <button type="button" class="danger" @click="setStatus(openItem, 'cancelled')">
            {{ t('schedule.yesCancel') }}
          </button>
          <button type="button" class="link" @click="asking = false">
            {{ t('schedule.keep') }}
          </button>
        </div>
      </template>
      <template v-else>
        <div class="actions">
          <button v-if="openActions.signUp" type="button" @click="signUp(openItem)">
            {{ t('schedule.signUp') }}
          </button>
          <button
            v-if="openActions.confirm"
            type="button"
            @click="setStatus(openItem, 'confirmed')"
          >
            {{ t('schedule.confirm') }}
          </button>
          <button
            v-if="openActions.cancel"
            type="button"
            class="link danger"
            @click="asking = true"
          >
            {{ t('schedule.cancel') }}
          </button>
        </div>
        <template v-if="openActions.propose">
          <p class="sub">{{ t('schedule.proposeTo') }}</p>
          <div class="people">
            <button
              v-for="member in members"
              :key="member.user_id"
              type="button"
              class="person"
              @click="propose(openItem, member)"
            >
              {{ member.display_name }}
            </button>
          </div>
        </template>
      </template>
      <button type="button" class="close link" :aria-label="t('schedule.close')" @click="close">
        ×
      </button>
    </div>
  </template>
</template>

<style scoped>
.weeks {
  display: grid;
  gap: 20px;
}

.week h2 {
  margin: 0 0 6px;
  font-variant-numeric: tabular-nums;
}

.line {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.line::before,
.line::after {
  content: '';
  height: 2px;
  background: var(--fg);
}

.line::before {
  flex: 0 0 16px;
}

.line::after {
  flex: 1;
}

.line.period {
  color: var(--muted);
}

.line.period::before,
.line.period::after {
  background: var(--muted);
}

.days {
  --hour-px: 36px;
  --lane-px: 44px;
  display: grid;
  grid-template-columns: 2.4rem repeat(var(--columns), minmax(0, 1fr));
  gap: 0 6px;
}

.day {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 4px;
  min-width: 0;
}

.day-head {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  min-height: 1.5em;
}

.day.past .day-head {
  color: var(--muted);
}

.day.past .track {
  opacity: 0.5;
  filter: grayscale(0.7);
}

.day.after .track {
  filter: grayscale(1);
}

.track {
  position: relative;
  height: calc(var(--hours) * var(--hour-px));
  border-radius: 6px;
  background-color: var(--surface);
  background-image: linear-gradient(to bottom, var(--line) 1px, transparent 1px);
  background-size: 100% calc(100% / var(--hours));
}

.axis .track {
  background: none;
}

.tick {
  position: absolute;
  top: calc(var(--p) * 100%);
  right: 4px;
  transform: translateY(-50%);
  font-size: 11px;
  color: var(--muted);
}

.tick:first-child {
  transform: none;
}

.tick:last-child {
  transform: translateY(-100%);
}

.track ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.occ {
  position: absolute;
  box-sizing: border-box;
  top: calc(var(--s) * 100% + 1px);
  height: calc((var(--e) - var(--s)) * 100% - 2px);
  left: calc(var(--lane) / var(--lanes) * 100% + 1px);
  width: calc(100% / var(--lanes) - 2px);
  border-radius: 5px;
  border: 1px solid transparent;
  border-left-width: 4px;
  overflow: hidden;
}

.occ.confirmed {
  background: var(--ok-soft);
  border-color: var(--ok);
}

.occ.proposed {
  background: var(--warn-soft);
  border-color: var(--warn);
}

.occ.free,
.occ.cancelled {
  background: var(--bad-soft);
  border-color: var(--bad);
}

.occ.obsolete {
  border-style: dashed;
  background-image: repeating-linear-gradient(
    135deg,
    transparent 0 6px,
    color-mix(in srgb, var(--fg) 8%, transparent) 6px 12px
  );
}

.occ.open {
  outline: 2px solid var(--fg);
  outline-offset: 1px;
}

.occ-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  height: 100%;
  padding: 2px 6px;
  border: 0;
  border-radius: 0;
  background: none;
  color: var(--fg);
  font: inherit;
  font-size: 13px;
  text-align: left;
}

.times {
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.name {
  font-weight: 600;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.free .name {
  font-weight: 400;
  font-style: italic;
  color: var(--bad);
}

.cancelled .name {
  font-weight: 400;
  color: var(--muted);
}

.tag {
  font-size: 11px;
  font-weight: 600;
}

.closure {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
  padding: 4px;
  font-size: 13px;
  color: var(--muted);
  background: repeating-linear-gradient(45deg, var(--line) 0 2px, transparent 2px 12px);
  border-radius: 6px;
}

.closure strong {
  color: var(--fg);
}

.more {
  margin-top: 20px;
}

.menu {
  position: fixed;
  z-index: 10;
  width: min(280px, calc(100vw - 32px));
  display: grid;
  gap: 10px;
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgb(0 0 0 / 0.18);
}

.menu p {
  margin: 0;
}

.menu-title {
  font-weight: 600;
  padding-right: 24px;
}

.menu .danger {
  background: var(--bad);
  color: var(--surface);
}

.menu .link.danger {
  background: none;
  color: var(--bad);
}

.people {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.person {
  padding: 4px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--bg);
  color: var(--fg);
  font-weight: 400;
}

.close {
  position: absolute;
  top: 8px;
  right: 12px;
  color: var(--muted);
  text-decoration: none;
  font-size: 18px;
}

@media (max-width: 560px) {
  .days {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .day {
    grid-template-columns: 4.2rem minmax(0, 1fr);
    grid-template-rows: none;
    align-items: stretch;
  }

  .day-head {
    white-space: normal;
    line-height: 1.2;
    align-self: center;
  }

  .track {
    height: calc(var(--day-lanes, 1) * var(--lane-px));
    background-image: linear-gradient(to right, var(--line) 1px, transparent 1px);
    background-size: calc(100% / var(--hours)) 100%;
  }

  .axis .track {
    height: 1.2em;
  }

  .tick {
    top: 0;
    right: auto;
    left: calc(var(--p) * 100%);
    transform: translateX(-50%);
  }

  .tick:first-child {
    transform: none;
  }

  .tick:last-child {
    transform: translateX(-100%);
  }

  .tick.minor {
    visibility: hidden;
  }

  .occ {
    left: calc(var(--s) * 100% + 1px);
    width: calc((var(--e) - var(--s)) * 100% - 2px);
    top: calc(var(--lane) / var(--lanes) * 100% + 1px);
    height: calc(100% / var(--lanes) - 2px);
  }

  .times {
    display: none;
  }

  .menu {
    left: 16px !important;
    right: 16px;
    top: auto !important;
    bottom: 16px;
    width: auto;
  }
}
</style>
