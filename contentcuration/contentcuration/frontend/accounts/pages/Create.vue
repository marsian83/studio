<template>

  <ImmersiveModalLayout
    :previousPage="{ name: 'Main' }"
    :appBarText="$tr('backToLoginButton')"
    backButton
  >
    <VImg
      height="200"
      maxHeight="100"
      contain
      :lazy-src="require('shared/images/kolibri-logo.svg')"
      :src="require('shared/images/kolibri-logo.svg')"
    />
    <h2 ref="top" class="mb-4 primary--text text-xs-center">
      {{ $tr('createAnAccountTitle') }}
    </h2>
    <VLayout justify-center class="px-4">
      <VForm ref="form" v-model="valid" lazy-validation @submit.prevent="submit">
        <Banner :value="!valid" error class="mb-4">
          {{ registrationFailed ? $tr('registrationFailed') : $tr('errorsMessage') }}
        </Banner>
        <Banner :value="offline" error class="mb-4">
          {{ $tr('registrationFailedOffline') }}
        </Banner>
        <!-- Basic information -->
        <h1 class="font-weight-bold my-2 subheading">
          {{ $tr('basicInformationHeader') }}
        </h1>
        <TextField
          v-model="form.first_name"
          maxlength="100"
          counter
          :label="$tr('firstNameLabel')"
          autofocus
        />
        <TextField
          v-model="form.last_name"
          maxlength="100"
          counter
          :label="$tr('lastNameLabel')"
        />
        <EmailField
          v-model="form.email"
          maxlength="100"
          counter
          :disabled="Boolean($route.query.email)"
          :error-messages="emailErrors"
          @input="emailErrors = []"
        />
        <PasswordField
          v-model="form.password1"
          :label="$tr('passwordLabel')"
        />
        <PasswordField
          v-model="form.password2"
          :additionalRules="passwordConfirmRules"
          :label="$tr('confirmPasswordLabel')"
        />

        <!-- Usage -->
        <VInput required :rules="usageRules" class="mt-2" />
        <h1 class="font-weight-bold mb-2 subheading">
          {{ $tr('usageLabel') }}*
        </h1>
        <div v-for="option in usageOptions" :key="option.id">
          <Checkbox
            v-model="form.uses"
            :label="option.label"
            :value="option.id"
          />
          <VSlideYTransition>
            <TextField
              v-if="showStorageField(option.id)"
              v-model="form.storage"
              :label="$tr('storingUsagePlaceholder')"
              :placeholder="$tr('storingUsageExample')"
              class="ml-4 my-1"
            />
            <TextArea
              v-else-if="showOtherField(option.id)"
              v-model="form.other_use"
              :label="$tr('otherUsagePlaceholder')"
              class="ml-4 my-2"
            />
          </VSlideYTransition>
        </div>


        <!-- Location -->
        <VInput required :rules="locationRules" class="mt-4" />
        <h1 class="font-weight-bold my-2 subheading">
          {{ $tr('locationLabel') }}*
        </h1>
        <CountryField v-model="form.locations" clearable />

        <!-- Source -->
        <VInput required :rules="sourceRules" class="mt-2" />
        <h1 class="font-weight-bold my-2 subheading">
          {{ $tr('sourceLabel') }}*
        </h1>
        <DropdownWrapper>
          <template #default="{ attach, menuProps }">
            <VSelect
              v-model="form.source"
              :items="sourceOptions"
              item-text="label"
              item-value="id"
              box
              :menu-props="menuProps"
              :attach="attach"
              :label="$tr('sourcePlaceholder')"
            />
          </template>
        </DropdownWrapper>
        <VSlideYTransition>
          <TextArea
            v-if="form.source === sources.ORGANIZATION"
            v-model="form.organization"
            :label="$tr('organizationSourcePlaceholder')"
          />
          <TextArea
            v-else-if="form.source === sources.CONFERENCE"
            v-model="form.conference"
            :label="$tr('conferenceSourcePlaceholder')"
          />
          <TextArea
            v-else-if="form.source === sources.OTHER"
            v-model="form.other_source"
            :label="$tr('otherSourcePlaceholder')"
          />
        </VSlideYTransition>

        <!-- Terms of service -->
        <ActionLink
          class="mt-4"
          :text="$tr('viewToSLink')"
          @click="showTermsOfService"
        />
        <Checkbox
          v-model="form.accepted_tos"
          :label="$tr('ToSCheck')"
          required
          :rules="tosRules"
          :hide-details="false"
          class="my-1 policy-checkbox"
        />

        <!-- Policy -->
        <ActionLink
          class="mt-2"
          :text="$tr('viewPrivacyPolicyLink')"
          @click="showPrivacyPolicy"
        />
        <Checkbox
          v-model="form.accepted_policy"
          :label="$tr('privacyPolicyCheck')"
          required
          :rules="policyRules"
          :hide-details="false"
          class="mb-3 mt-1 policy-checkbox"
        />

        <p class="mb-4">
          {{ $tr('contactMessage') }}
        </p>
        <VBtn color="primary" large :disabled="offline" type="submit">
          {{ $tr('finishButton') }}
        </VBtn>
      </VForm>

    </VLayout>
    <PolicyModals />
  </ImmersiveModalLayout>

</template>


<script>

  import { mapActions, mapGetters, mapState } from 'vuex';
  import { uses, sources } from '../constants';
  import TextField from 'shared/views/form/TextField';
  import EmailField from 'shared/views/form/EmailField';
  import PasswordField from 'shared/views/form/PasswordField';
  import TextArea from 'shared/views/form/TextArea';
  import CountryField from 'shared/views/form/CountryField';
  import PolicyModals from 'shared/views/policies/PolicyModals';
  import ImmersiveModalLayout from 'shared/layouts/ImmersiveModalLayout';
  import Banner from 'shared/views/Banner';
  import Checkbox from 'shared/views/form/Checkbox';
  import { policies } from 'shared/constants';
  import DropdownWrapper from 'shared/views/form/DropdownWrapper';

  export default {
    name: 'Create',
    components: {
      DropdownWrapper,
      ImmersiveModalLayout,
      TextField,
      EmailField,
      PasswordField,
      TextArea,
      CountryField,
      PolicyModals,
      Banner,
      Checkbox,
    },
    data() {
      return {
        valid: true,
        registrationFailed: false,
        emailErrors: [],
        form: {
          first_name: '',
          last_name: '',
          email: '',
          password1: '',
          password2: '',
          uses: [],
          storage: '',
          other_use: '',
          locations: [],
          source: '',
          organization: '',
          conference: '',
          other_source: '',
          accepted_policy: false,
          accepted_tos: false,
        },
      };
    },
    computed: {
      ...mapState({
        offline: state => !state.connection.online,
      }),
      ...mapGetters('policies', ['getPolicyAcceptedData']),
      passwordConfirmRules() {
        return [value => (this.form.password1 === value ? true : this.$tr('passwordMatchMessage'))];
      },
      tosRules() {
        return [value => (value ? true : this.$tr('ToSRequiredMessage'))];
      },
      policyRules() {
        return [value => (value ? true : this.$tr('privacyPolicyRequiredMessage'))];
      },
      usageOptions() {
        return [
          {
            id: uses.ORGANIZING,
            label: this.$tr('organizingUsageOption'),
          },
          {
            id: uses.FINDING,
            label: this.$tr('findingUsageOption'),
          },
          {
            id: uses.SEQUENCING,
            label: this.$tr('sequencingUsageOption'),
          },
          {
            id: uses.CREATING_EXERCISES,
            label: this.$tr('creatingExercisesUsageOption'),
          },
          {
            id: uses.SHARING,
            label: this.$tr('sharingUsageOption'),
          },
          {
            id: uses.STORING,
            label: this.$tr('storingUsageOption'),
          },
          {
            id: uses.TAGGING,
            label: this.$tr('taggingUsageOption'),
          },
          {
            id: uses.OTHER,
            label: this.$tr('otherUsageOption'),
          },
        ];
      },
      usageRules() {
        return [() => (this.form.uses.length ? true : this.$tr('fieldRequiredMessage'))];
      },
      locationRules() {
        return [() => (this.form.locations.length ? true : this.$tr('fieldRequiredMessage'))];
      },
      sources() {
        return sources;
      },
      sourceOptions() {
        return [
          {
            id: sources.ORGANIZATION,
            label: this.$tr('organizationSourceOption'),
            additional: {
              model: this.form.organization,
              label: this.$tr('organizationSourcePlaceholder'),
            },
          },
          {
            id: sources.WEBSITE,
            label: this.$tr('websiteSourceOption'),
          },
          {
            id: sources.NEWSLETTER,
            label: this.$tr('newsletterSourceOption'),
          },
          {
            id: sources.FORUM,
            label: this.$tr('forumSourceOption'),
          },
          {
            id: sources.GITHUB,
            label: this.$tr('githubSourceOption'),
          },
          {
            id: sources.SOCIAL_MEDIA,
            label: this.$tr('socialMediaSourceOption'),
          },
          {
            id: sources.CONFERENCE,
            label: this.$tr('conferenceSourceOption'),
            additional: {
              model: this.form.conference,
              label: this.$tr('conferenceSourcePlaceholder'),
            },
          },
          {
            id: sources.CONVERSATION,
            label: this.$tr('conversationSourceOption'),
          },
          {
            id: sources.DEMO,
            label: this.$tr('personalDemoSourceOption'),
          },
          {
            id: sources.OTHER,
            label: this.$tr('otherSourceOption'),
            additional: {
              model: this.form.other_source,
              label: this.$tr('otherSourcePlaceholder'),
            },
          },
        ];
      },
      sourceRules() {
        return [() => (this.form.source.length ? true : this.$tr('fieldRequiredMessage'))];
      },
      clean() {
        return data => {
          let cleanedData = { ...data, policies: {} };
          Object.keys(cleanedData).forEach(key => {
            // Trim text fields
            if (key === 'source') {
              if (cleanedData[key] === sources.ORGANIZATION) {
                cleanedData[key] = `${cleanedData.organization} (organization)`;
              } else if (cleanedData[key] === sources.CONFERENCE) {
                cleanedData[key] = `${cleanedData.conference} (conference)`;
              } else if (cleanedData[key] === sources.OTHER) {
                cleanedData[key] = `${cleanedData.other_source} (other)`;
              } else {
                cleanedData[key] = cleanedData[key].trim();
              }
            } else if (typeof cleanedData[key] === 'string') {
              cleanedData[key] = cleanedData[key].trim();
            } else if (key === 'locations') {
              cleanedData[key] = cleanedData[key].join('|');
            } else if (key === 'uses') {
              cleanedData[key] = cleanedData[key]
                .map(use => {
                  if (use === uses.OTHER) {
                    return `${cleanedData.other_use} (other)`;
                  } else if (use === uses.STORING) {
                    return `storage (${cleanedData.storage})`;
                  }
                  return use;
                })
                .join('|');
            } else if (key === 'accepted_policy') {
              cleanedData.policies = {
                ...cleanedData.policies,
                ...this.getPolicyAcceptedData(policies.PRIVACY),
              };
            } else if (key === 'accepted_tos') {
              cleanedData.policies = {
                ...cleanedData.policies,
                ...this.getPolicyAcceptedData(policies.TERMS_OF_SERVICE),
              };
            }
          });
          cleanedData.policies = JSON.stringify(cleanedData.policies);
          return cleanedData;
        };
      },
    },
    beforeMount() {
      this.form.email = this.$route.query.email || '';
    },
    methods: {
      ...mapActions('account', ['register']),
      ...mapActions('policies', ['openPolicy']),
      showTermsOfService() {
        this.openPolicy(policies.TERMS_OF_SERVICE);
      },
      showPrivacyPolicy() {
        this.openPolicy(policies.PRIVACY);
      },
      showStorageField(id) {
        return id === uses.STORING && this.form.uses.includes(id);
      },
      showOtherField(id) {
        return id === uses.OTHER && this.form.uses.includes(id);
      },

      submit() {
        if (this.$refs.form.validate()) {
          let cleanedData = this.clean(this.form);
          return this.register(cleanedData)
            .then(() => {
              this.$router.push({ name: 'ActivationSent' });
            })
            .catch(error => {
              if (error.message === 'Network Error') {
                this.$refs.top.scrollIntoView({ behavior: 'smooth' });
              } else if (error.response.status === 403) {
                this.emailErrors = [this.$tr('emailExistsMessage')];
              } else if (error.response.status === 405) {
                this.$router.push({ name: 'AccountNotActivated' });
              } else {
                this.registrationFailed = true;
                this.valid = false;
              }
            });
        } else if (this.$refs.top.scrollIntoView) {
          this.$refs.top.scrollIntoView({ behavior: 'smooth' });
        }
        return Promise.resolve();
      },
    },
    $trs: {
      backToLoginButton: 'Sign in',
      createAnAccountTitle: 'Create an account',
      fieldRequiredMessage: 'Field is required',
      errorsMessage: 'Please fix the errors below',
      registrationFailed: 'There was an error registering your account. Please try again',
      registrationFailedOffline:
        'You seem to be offline. Please connect to the internet to create an account.',

      // Basic information strings
      basicInformationHeader: 'Basic information',
      firstNameLabel: 'First name',
      lastNameLabel: 'Last name',
      emailExistsMessage: 'An account with this email already exists',
      passwordLabel: 'Password',
      confirmPasswordLabel: 'Confirm password',
      passwordMatchMessage: "Passwords don't match",

      // Usage question
      usageLabel: 'How do you plan on using Kolibri Studio (check all that apply)',
      organizingUsageOption: 'Organizing or aligning existing materials',
      findingUsageOption: 'Finding and adding additional content sources',
      sequencingUsageOption: 'Using prerequisites to put materials in a sequence',
      creatingExercisesUsageOption: 'Creating exercises',
      sharingUsageOption: 'Sharing materials publicly',
      storingUsageOption: 'Storing materials for private or local use',
      storingUsagePlaceholder: 'How much storage do you need?',
      storingUsageExample: 'e.g. 500MB',
      taggingUsageOption: 'Tagging content sources for discovery',
      otherUsageOption: 'Other',
      otherUsagePlaceholder: 'Please describe',

      // Location question
      locationLabel: 'Where do you plan to use Kolibri Studio? (check all that apply)',

      // Introduction question
      sourceLabel: 'How did you hear about us?',
      sourcePlaceholder: 'Select one',
      organizationSourceOption: 'Organization',
      organizationSourcePlaceholder: 'Name of organization',
      websiteSourceOption: 'Learning Equality website',
      newsletterSourceOption: 'Learning Equality newsletter',
      forumSourceOption: 'Learning Equality community forum',
      githubSourceOption: 'Learning Equality GitHub',
      socialMediaSourceOption: 'Social media',
      conferenceSourceOption: 'Conference',
      conferenceSourcePlaceholder: 'Name of conference',
      conversationSourceOption: 'Conversation with Learning Equality',
      personalDemoSourceOption: 'Personal demo',
      otherSourceOption: 'Other',
      otherSourcePlaceholder: 'Please describe',

      // Privacy policy + terms of service
      viewToSLink: 'View terms of service',
      ToSCheck: 'I have read and agree to the terms of service',
      ToSRequiredMessage: 'Please accept our terms of service',

      viewPrivacyPolicyLink: 'View privacy policy',
      privacyPolicyCheck: 'I have read and agree to the privacy policy',
      privacyPolicyRequiredMessage: 'Please accept our privacy policy',
      contactMessage: 'Questions or concerns? Please email us at content@learningequality.org',
      finishButton: 'Finish',
    },
  };

</script>


<style lang="less" scoped>

  .v-text-field {
    margin-top: 8px !important;
  }

  .policy-checkbox /deep/ .v-input__slot {
    margin-bottom: 4px !important;

    label {
      color: var(--v-grey-darken1) !important;
    }
  }

  iframe {
    width: 100%;
    min-height: 400px;
    padding: 8px;
    padding-right: 0;
    border: 0;
  }

</style>
