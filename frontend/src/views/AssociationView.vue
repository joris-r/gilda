<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  addMember,
  ApiError,
  changeRole,
  getAssociation,
  type Association,
  type Member,
  type Role,
} from '../api'
import { useSession } from '../session'

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const { user } = useSession()

const association = ref<Association>()
const confirming = ref<string>()
const message = ref<{ text: string; ok: boolean }>()

const displayName = ref('')
const email = ref('')
const role = ref<Role>('volunteer')

const isManager = computed(() => association.value?.role === 'manager')
const members = computed(() =>
  [...(association.value?.members ?? [])].sort(
    (a, b) =>
      Number(b.role === 'manager') - Number(a.role === 'manager') ||
      a.display_name.localeCompare(b.display_name),
  ),
)

async function load() {
  association.value = await getAssociation(props.id)
}

watch(() => props.id, load, { immediate: true })

function otherRole(member: Member): Role {
  return member.role === 'manager' ? 'volunteer' : 'manager'
}

async function confirmRole(member: Member) {
  const newRole = otherRole(member)
  confirming.value = undefined
  try {
    const updated = await changeRole(props.id, member.user_id, newRole)
    member.role = updated.role
    if (association.value && updated.user_id === user.value?.id)
      association.value.role = updated.role
    message.value = {
      ok: true,
      text: t('association.roleChanged', {
        name: updated.display_name,
        role: t(`roleNames.${updated.role}`),
      }),
    }
  } catch (e) {
    const text =
      e instanceof ApiError && e.status === 409 ? t('association.lastManager') : t('error')
    message.value = { ok: false, text }
  }
}

async function add() {
  const name = displayName.value
  try {
    const member = await addMember(props.id, name, email.value, role.value)
    await load()
    message.value = { ok: true, text: t('association.added', { name: member.display_name }) }
    displayName.value = ''
    email.value = ''
    role.value = 'volunteer'
  } catch (e) {
    const text =
      e instanceof ApiError && e.status === 409
        ? t('association.alreadyMember', { name })
        : t('error')
    message.value = { ok: false, text }
  }
}
</script>

<template>
  <p class="hint">
    <RouterLink to="/">{{ t('association.back') }}</RouterLink>
  </p>
  <template v-if="association">
    <h1>{{ association.name }}</h1>
    <p class="links">
      <RouterLink :to="`/associations/${id}/schedule`">{{ t('association.schedule') }}</RouterLink>
      <RouterLink :to="`/associations/${id}/opening`">{{ t('association.opening') }}</RouterLink>
    </p>
    <h2>{{ t('association.members') }}</h2>
    <ul class="list">
      <li v-for="member in members" :key="member.user_id">
        <div>
          {{ member.display_name }}
          <span v-if="!member.has_account" class="no-account">{{
            t('association.noAccount')
          }}</span>
          <span v-else-if="!member.email_verified" class="no-account">{{
            t('association.pending')
          }}</span>
          <div class="sub">{{ member.email }}</div>
        </div>
        <div v-if="isManager && confirming === member.user_id" class="actions">
          <span class="sub">{{
            t('association.confirmRole', {
              name: member.display_name,
              role: t(`roleNames.${otherRole(member)}`),
            })
          }}</span>
          <button type="button" @click="confirmRole(member)">
            {{ t('association.confirm') }}
          </button>
          <button type="button" class="link" @click="confirming = undefined">
            {{ t('association.cancel') }}
          </button>
        </div>
        <div v-else class="actions">
          <span :class="['role', member.role]">{{ t(`roles.${member.role}`) }}</span>
          <button v-if="isManager" type="button" class="link" @click="confirming = member.user_id">
            {{ t('association.changeRole') }}
          </button>
        </div>
      </li>
    </ul>
    <p v-if="message" :class="message.ok ? 'ok' : 'error'">{{ message.text }}</p>
    <template v-if="isManager">
      <h2>{{ t('association.addMember') }}</h2>
      <form class="panel" @submit.prevent="add">
        <label>
          {{ t('fields.displayName') }}
          <input v-model="displayName" required />
        </label>
        <label>
          {{ t('fields.email') }}
          <input v-model="email" type="email" required />
        </label>
        <label>
          {{ t('fields.role') }}
          <select v-model="role">
            <option value="volunteer">{{ t('roles.volunteer') }}</option>
            <option value="manager">{{ t('roles.manager') }}</option>
          </select>
        </label>
        <button type="submit">{{ t('association.submit') }}</button>
      </form>
    </template>
  </template>
</template>
