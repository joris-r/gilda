<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { PlanningPeriod, Schedule } from '../api'
import { addDays, formatDate, isoWeek, longDay, minutes, mondayOf, weekdayIndex } from '../dates'
import { actions, dayLabel, times, type Item } from '../schedule'

const props = defineProps<{
  schedule: Schedule
  period: PlanningPeriod | null
  /** Today in the association's timezone. */
  day0: string
  firstMonday: string
  weeks: number
  openKey: string | undefined
  userId: string | undefined
  isManager: boolean
}>()
const emit = defineEmits<{ toggle: [item: Item, anchor: DOMRect] }>()
const { t, locale } = useI18n()

/** Each day's items, with lanes so that overlapping ones sit side by side. */
const itemsByDate = computed(() => {
  const byDate = new Map<string, Item[]>()
  const push = (item: Omit<Item, 'key' | 'lane' | 'lanes'>) => {
    const list = byDate.get(item.date) ?? []
    list.push({ ...item, key: `${item.date} ${item.start} ${item.end}`, lane: 0, lanes: 1 })
    byDate.set(item.date, list)
  }
  for (const o of props.schedule.occurrences) push({ ...o, obsolete: false })
  for (const r of props.schedule.obsolete) {
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
  Array.from({ length: props.weeks }, (_, n) => {
    const monday = addDays(props.firstMonday, 7 * n)
    const period = props.period
    return {
      monday,
      current: monday === mondayOf(props.day0),
      periodStarts: period !== null && mondayOf(period.first) === monday,
      periodEnds: period !== null && mondayOf(period.last) === monday,
      days: columns.value.map((column) => {
        const date = addDays(monday, column)
        const items = itemsByDate.value.get(date) ?? []
        return {
          date,
          items,
          lanes: Math.max(1, ...items.map((i) => i.lanes)),
          closure: props.schedule.closures.find((c) => c.first <= date && date <= c.last),
        }
      }),
    }
  }),
)

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

function clickable(item: Item) {
  return (
    item.date >= props.day0 &&
    Object.values(actions(item, props.userId, props.isManager)).some(Boolean)
  )
}

/** The accessible name of an item: its times, which it does not show, then what it shows. */
function label(item: Item) {
  const r = item.registration
  return [
    times(item),
    r?.display_name,
    r?.status === 'proposed' ? '?' : undefined,
    item.obsolete ? t('schedule.obsolete') : undefined,
  ]
    .filter(Boolean)
    .join(' ')
}

function click(item: Item, event: MouseEvent) {
  if (clickable(item))
    emit('toggle', item, (event.currentTarget as HTMLElement).getBoundingClientRect())
}
</script>

<template>
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
        <h2>{{ t('schedule.week', { n: isoWeek(week.monday) }) }}</h2>
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
            :aria-label="dayLabel(day.date, locale)"
            :class="['day', { past: day.date < day0, after: period && day.date > period.last }]"
          >
            <div class="day-head">{{ dayLabel(day.date, locale) }}</div>
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
                    :aria-label="label(item)"
                    @click.stop="click(item, $event)"
                  >
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
}
</style>
