<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  addMember,
  ApiError,
  changeRole,
  getAssociation,
  revokeMemberLink,
  type Association,
  type Member,
  type Role,
} from '../api'
import { useLocation } from '../location'
import { useSession } from '../session'

/** Members shown before "Show all". */
const FIRST_MEMBERS = 5

const props = defineProps<{ id: string }>()
const { t } = useI18n()
const { user } = useSession()
const location = useLocation()

const association = ref<Association>()
/** The member whose line asks to confirm an action, and which one. */
const confirming = ref<{ userId: string; action: 'role' | 'link' }>()
const message = ref<{ text: string; ok: boolean }>()
const showAll = ref(false)
const adding = ref(false)

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
const shownMembers = computed(() =>
  showAll.value ? members.value : members.value.slice(0, FIRST_MEMBERS),
)

async function load() {
  const found = await getAssociation(props.id)
  association.value = found
  location.value = {
    association: { id: found.id, name: found.name },
    screen: 'association.members',
  }
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

async function confirmRevoke(member: Member) {
  confirming.value = undefined
  try {
    await revokeMemberLink(props.id, member.user_id)
    member.access_link = false
    message.value = { ok: true, text: t('association.linkRevoked', { name: member.display_name }) }
  } catch {
    message.value = { ok: false, text: t('error') }
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
  <template v-if="association">
    <ul class="list">
      <li v-for="member in shownMembers" :key="member.user_id">
        <div>
          {{ member.display_name }}
          <span v-if="!member.email_verified" class="no-account">{{
            t('association.notJoined')
          }}</span>
          <div class="sub">{{ member.email }}</div>
        </div>
        <div v-if="isManager && confirming?.userId === member.user_id" class="actions">
          <span v-if="confirming.action === 'link'" class="sub">{{
            t('association.confirmRevokeLink', { name: member.display_name })
          }}</span>
          <span v-else class="sub">{{
            t('association.confirmRole', {
              name: member.display_name,
              role: t(`roleNames.${otherRole(member)}`),
            })
          }}</span>
          <button
            type="button"
            @click="confirming.action === 'link' ? confirmRevoke(member) : confirmRole(member)"
          >
            {{ t('association.confirm') }}
          </button>
          <button type="button" class="link" @click="confirming = undefined">
            {{ t('association.cancel') }}
          </button>
        </div>
        <div v-else class="actions">
          <span :class="['role', member.role]">{{ t(`roles.${member.role}`) }}</span>
          <button
            v-if="isManager"
            type="button"
            class="link"
            @click="confirming = { userId: member.user_id, action: 'role' }"
          >
            {{ t('association.changeRole') }}
          </button>
          <button
            v-if="isManager && member.access_link"
            type="button"
            class="link"
            @click="confirming = { userId: member.user_id, action: 'link' }"
          >
            {{ t('association.revokeLink') }}
          </button>
        </div>
      </li>
    </ul>
    <p v-if="!showAll && members.length > FIRST_MEMBERS" class="more">
      <button type="button" class="link" @click="showAll = true">
        {{ t('association.showAll', { n: members.length }) }}
      </button>
    </p>
    <p v-if="message" :class="message.ok ? 'ok' : 'error'">{{ message.text }}</p>
    <button v-if="isManager && !adding" type="button" class="add" @click="adding = true">
      {{ t('association.addMember') }}
    </button>
    <template v-if="isManager && adding">
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

<style scoped>
.more {
  margin: 12px 0 0;
}

.add {
  margin-top: 24px;
}
</style>
