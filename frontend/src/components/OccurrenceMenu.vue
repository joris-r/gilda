<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type {
  Member,
  MemberAbsence,
  MemberNote,
  Preference,
  PreferenceValue,
  RegistrationCount,
  Slot,
} from '../api'
import { WEEKDAYS, weekdayIndex } from '../dates'
import { dayLabel, times, type Actions, type Item } from '../schedule'

const props = defineProps<{
  item: Item
  actions: Actions
  /** The rectangle of the item the menu opens from. */
  anchor: DOMRect
  members: Member[]
  slots: Slot[]
  preferences: Preference[]
  counts: RegistrationCount[] | null
  absences: MemberAbsence[]
  notes: MemberNote[]
}>()
const emit = defineEmits<{
  signUp: []
  propose: [member: Member]
  setStatus: [status: 'confirmed' | 'cancelled']
  close: []
}>()
const { t, locale } = useI18n()

const asking = ref(false)
const menu = ref<HTMLElement>()
const menuPosition = ref({ left: props.anchor.right + 8, top: props.anchor.top })

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

onMounted(() => placeMenu(props.anchor))

/** A member's preference for the slot of the item; null when they have stated none. */
function preferenceFor(member: Member) {
  const slot = props.slots.find(
    (s) =>
      WEEKDAYS.indexOf(s.weekday) === weekdayIndex(props.item.date) &&
      s.start === props.item.start &&
      s.end === props.item.end,
  )
  return (
    props.preferences.find((p) => p.slot_id === slot?.id && p.user_id === member.user_id)?.value ??
    null
  )
}

function countOf(member: Member) {
  return props.counts?.find((c) => c.user_id === member.user_id)?.count ?? 0
}

function isAbsent(member: Member) {
  return props.absences.some(
    (a) => a.user_id === member.user_id && a.first <= props.item.date && props.item.date <= a.last,
  )
}

/** The member's note for the tooltip of their name; undefined when empty. */
function noteOf(member: Member) {
  return props.notes.find((n) => n.user_id === member.user_id)?.text || undefined
}

const RANKS: (PreferenceValue | null)[] = ['preferred', 'possible', null, 'unavailable']

function rankOf(member: Member) {
  return isAbsent(member) ? RANKS.length : RANKS.indexOf(preferenceFor(member))
}

/** The members in the order of R27; `members` comes sorted by display name. */
const people = computed(() =>
  props.members
    .map((member) => ({ member, rank: rankOf(member), count: countOf(member) }))
    .sort((a, b) => a.rank - b.rank || a.count - b.count),
)
</script>

<template>
  <div
    ref="menu"
    class="menu"
    role="dialog"
    :aria-label="`${dayLabel(item.date, locale)} ${times(item)}`"
    :style="{ left: `${menuPosition.left}px`, top: `${menuPosition.top}px` }"
    @click.stop
  >
    <p class="menu-title">{{ dayLabel(item.date, locale) }} · {{ times(item) }}</p>
    <template v-if="asking">
      <p>{{ t('schedule.askCancel') }}</p>
      <div class="actions">
        <button type="button" class="danger" @click="emit('setStatus', 'cancelled')">
          {{ t('schedule.yesCancel') }}
        </button>
        <button type="button" class="link" @click="asking = false">
          {{ t('schedule.keep') }}
        </button>
      </div>
    </template>
    <template v-else>
      <div class="actions">
        <button v-if="actions.signUp" type="button" @click="emit('signUp')">
          {{ t('schedule.signUp') }}
        </button>
        <button v-if="actions.confirm" type="button" @click="emit('setStatus', 'confirmed')">
          {{ t('schedule.confirm') }}
        </button>
        <button v-if="actions.cancel" type="button" class="link danger" @click="asking = true">
          {{ t('schedule.cancel') }}
        </button>
      </div>
      <template v-if="actions.propose">
        <p class="sub">{{ t('schedule.proposeTo') }}</p>
        <div class="people">
          <button
            v-for="{ member } in people"
            :key="member.user_id"
            type="button"
            :class="[
              'person',
              isAbsent(member)
                ? 'absent'
                : preferenceFor(member) && `preference-${preferenceFor(member)}`,
            ]"
            :title="noteOf(member)"
            @click="emit('propose', member)"
          >
            {{ member.display_name }}<template v-if="counts"> ({{ countOf(member) }})</template>
          </button>
        </div>
      </template>
    </template>
    <button
      type="button"
      class="close link"
      :aria-label="t('schedule.close')"
      @click="emit('close')"
    >
      ×
    </button>
  </div>
</template>

<style scoped>
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

.person.preference-preferred {
  background: var(--ok-soft);
  border-color: var(--ok);
}

.person.preference-possible {
  background: var(--warn-soft);
  border-color: var(--warn);
}

.person.preference-unavailable {
  background: var(--bad-soft);
  border-color: var(--bad);
}

.person.absent {
  background: var(--line);
  border-color: var(--muted);
  color: var(--muted);
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
  .menu {
    left: 16px !important;
    right: 16px;
    top: auto !important;
    bottom: 16px;
    width: auto;
  }
}
</style>
