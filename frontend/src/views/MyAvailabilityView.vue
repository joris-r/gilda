<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  addAbsence,
  ApiError,
  deleteAbsence,
  deletePreference,
  editAbsence,
  getNote,
  listAbsences,
  listPreferences,
  listSlots,
  setNote,
  setPreference,
  type Absence,
  type Association,
  type Preference,
  type PreferenceValue,
  type Slot,
} from '../api'
import AppDialog from '../components/AppDialog.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import IconButton from '../components/IconButton.vue'
import PreferenceSelect from '../components/PreferenceSelect.vue'
import UnknownAssociation from '../components/UnknownAssociation.vue'
import { formatDate, shortDayWithYear, today, WEEKDAYS } from '../dates'
import { useAssociationBySlug } from '../associationBySlug'
import { useLocation } from '../location'
import { useSession } from '../session'

const props = defineProps<{ slug: string }>()
const { id, unknown, read } = useAssociationBySlug(() => props.slug)
const { t, locale } = useI18n()
const location = useLocation()
const { user } = useSession()

const association = ref<Association>()
const slots = ref<Slot[]>([])
const preferences = ref<Preference[]>([])
const absences = ref<Absence[]>([])
const note = ref('')
const message = ref<string>()

/** The open dialog, with its error; an absence dialog names what it edits, if any. */
type Open =
  | { kind: 'absence'; error: string; editing?: Absence }
  | { kind: 'deleteAbsence'; absence: Absence }
  | { kind: 'note'; error: string }
const open = ref<Open>()

const first = ref('')
const last = ref('')
const text = ref('')

const sortedSlots = computed(() =>
  [...slots.value].sort(
    (a, b) =>
      WEEKDAYS.indexOf(a.weekday) - WEEKDAYS.indexOf(b.weekday) ||
      a.start.localeCompare(b.start) ||
      a.end.localeCompare(b.end),
  ),
)
const shownAbsences = computed(() => {
  const day = today(association.value!.timezone)
  return absences.value
    .filter((a) => a.last >= day)
    .sort((a, b) => a.first.localeCompare(b.first) || a.last.localeCompare(b.last))
})

async function load() {
  association.value = undefined
  const found = await read()
  if (!found) return
  ;[slots.value, preferences.value, absences.value, note.value] = await Promise.all([
    listSlots(id.value),
    listPreferences(id.value),
    listAbsences(id.value),
    getNote(id.value),
  ])
  association.value = found
  location.value = {
    association: { slug: found.slug, name: found.name },
    screen: 'availability.title',
  }
}

watch(() => props.slug, load, { immediate: true })

function dates(range: { first: string; last: string }) {
  const format = (iso: string) => formatDate(iso, locale.value, shortDayWithYear)
  return range.first === range.last
    ? format(range.first)
    : `${format(range.first)} – ${format(range.last)}`
}

function failure(e: unknown) {
  if (e instanceof ApiError && e.status === 400) return t('availability.invalid')
  return t('error')
}

function dialogError(error: string) {
  if (open.value && 'error' in open.value) open.value.error = error
}

function preferenceOf(slot: Slot) {
  return (
    preferences.value.find((p) => p.slot_id === slot.id && p.user_id === user.value!.id)?.value ??
    null
  )
}

async function choosePreference(slot: Slot, value: PreferenceValue | null) {
  message.value = undefined
  const userId = user.value!.id
  const others = preferences.value.filter((p) => !(p.slot_id === slot.id && p.user_id === userId))
  try {
    if (value === null) {
      await deletePreference(id.value, slot.id, userId)
      preferences.value = others
    } else {
      preferences.value = [...others, await setPreference(id.value, slot.id, userId, value)]
    }
  } catch (e) {
    message.value = failure(e)
  }
}

function openAbsence(editing?: Absence) {
  first.value = editing?.first ?? ''
  last.value = editing?.last ?? ''
  open.value = { kind: 'absence', error: '', editing }
}

async function saveAbsence(editing?: Absence) {
  try {
    if (editing) {
      const absence = await editAbsence(id.value, editing.id, first.value, last.value)
      absences.value = absences.value.map((a) => (a.id === absence.id ? absence : a))
    } else {
      absences.value.push(await addAbsence(id.value, first.value, last.value))
    }
    open.value = undefined
  } catch (e) {
    dialogError(failure(e))
  }
}

async function removeAbsence(absence: Absence) {
  open.value = undefined
  message.value = undefined
  try {
    await deleteAbsence(id.value, absence.id)
    absences.value = absences.value.filter((a) => a.id !== absence.id)
  } catch (e) {
    message.value = failure(e)
  }
}

function openNote() {
  text.value = note.value
  open.value = { kind: 'note', error: '' }
}

async function saveNote() {
  try {
    note.value = await setNote(id.value, text.value)
    open.value = undefined
  } catch (e) {
    dialogError(failure(e))
  }
}
</script>

<template>
  <UnknownAssociation v-if="unknown" />
  <template v-else-if="association">
    <section>
      <h2>{{ t('availability.preferences') }}</h2>
      <p v-if="!slots.length" class="hint">{{ t('availability.noSlots') }}</p>
      <ul v-else class="list">
        <li v-for="slot in sortedSlots" :key="slot.id">
          <span>{{ t(`weekdays.${slot.weekday}`) }}</span>
          <div class="actions">
            <span>{{ slot.start }}–{{ slot.end }}</span>
            <PreferenceSelect
              :value="preferenceOf(slot)"
              :aria-label="`${t(`weekdays.${slot.weekday}`)} ${slot.start}–${slot.end}`"
              @change="choosePreference(slot, $event)"
            />
          </div>
        </li>
      </ul>
    </section>

    <section>
      <div class="section-head">
        <h2>{{ t('availability.absences') }}</h2>
        <button type="button" class="add" @click="openAbsence()">
          <span aria-hidden="true">+</span> {{ t('availability.addAbsence') }}
        </button>
      </div>
      <p v-if="!shownAbsences.length" class="hint">{{ t('availability.noAbsences') }}</p>
      <ul v-else class="list">
        <li v-for="absence in shownAbsences" :key="absence.id">
          <span>{{ dates(absence) }}</span>
          <div class="line-actions">
            <IconButton
              icon="edit"
              :label="t('availability.editAbsence')"
              @click="openAbsence(absence)"
            />
            <IconButton
              icon="delete"
              :label="t('availability.deleteAbsence')"
              @click="open = { kind: 'deleteAbsence', absence }"
            />
          </div>
        </li>
      </ul>
    </section>

    <section>
      <div class="section-head">
        <h2>{{ t('availability.note') }}</h2>
        <IconButton icon="edit" :label="t('availability.editNote')" @click="openNote" />
      </div>
      <p v-if="note" class="note">{{ note }}</p>
      <p v-else class="hint">{{ t('availability.noNote') }}</p>
    </section>
    <p v-if="message" class="error">{{ message }}</p>

    <AppDialog
      v-if="open?.kind === 'absence'"
      :title="t(open.editing ? 'availability.editAbsence' : 'availability.addAbsence')"
      @close="open = undefined"
    >
      <form @submit.prevent="saveAbsence(open.editing)">
        <div class="fields">
          <label>
            {{ t('settings.first') }}
            <input v-model="first" type="date" required />
          </label>
          <label>
            {{ t('settings.last') }}
            <input v-model="last" type="date" required />
          </label>
        </div>
        <p v-if="open.error" class="error">{{ open.error }}</p>
        <div class="dialog-actions">
          <button type="submit">
            {{ t(open.editing ? 'settings.save' : 'availability.addAbsenceAction') }}
          </button>
          <button type="button" class="link" @click="open = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <AppDialog
      v-if="open?.kind === 'note'"
      :title="t('availability.note')"
      @close="open = undefined"
    >
      <form @submit.prevent="saveNote">
        <label>
          {{ t('availability.text') }}
          <textarea v-model="text" rows="4"></textarea>
        </label>
        <p v-if="open.error" class="error">{{ open.error }}</p>
        <div class="dialog-actions">
          <button type="submit">{{ t('settings.save') }}</button>
          <button type="button" class="link" @click="open = undefined">
            {{ t('dialog.cancel') }}
          </button>
        </div>
      </form>
    </AppDialog>

    <ConfirmDialog
      v-if="open?.kind === 'deleteAbsence'"
      :question="t('availability.confirmDeleteAbsence', { dates: dates(open.absence) })"
      :action="t('settings.deleteAction')"
      @confirm="removeAbsence(open.absence)"
      @cancel="open = undefined"
    />
  </template>
</template>

<style scoped>
.note {
  white-space: pre-line;
}
</style>
