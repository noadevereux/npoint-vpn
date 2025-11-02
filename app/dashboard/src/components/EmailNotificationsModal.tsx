import {
  Box,
  Button,
  Checkbox,
  Divider,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Spinner,
  Switch,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect, useMemo } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery } from "react-query";
import { fetch } from "service/http";
import {
  EmailNotificationConfig,
  EmailNotificationConfigUpdate,
  EmailNotificationTrigger,
} from "types/EmailNotifications";
import { Input } from "./Input";

type TriggerMetadata = {
  key: EmailNotificationTrigger;
  label: string;
  description: string;
};

type FormState = {
  smtp: {
    host: string;
    port: number;
    username: string;
    password: string;
    from_email: string;
    from_name: string;
    use_tls: boolean;
    use_ssl: boolean;
    has_password: boolean;
    removePassword: boolean;
  };
  preferences: Record<EmailNotificationTrigger, boolean>;
};

const QUERY_KEY = "email-notifications";

const TRIGGERS: TriggerMetadata[] = [
  "user_created",
  "user_updated",
  "user_deleted",
  "user_limited",
  "user_expired",
  "user_enabled",
  "user_disabled",
  "data_usage_reset",
  "data_reset_by_next",
  "subscription_revoked",
  "reached_usage_percent",
  "reached_days_left",
].map((key) => ({
  key: key as EmailNotificationTrigger,
  label: `emailNotifications.triggers.${key}`,
  description: `emailNotifications.triggerDescriptions.${key}`,
}));

const createDefaultPreferences = () => {
  return TRIGGERS.reduce(
    (acc, trigger) => ({ ...acc, [trigger.key]: false }),
    {} as Record<EmailNotificationTrigger, boolean>
  );
};

const mapConfigToForm = (
  config: EmailNotificationConfig | null,
): FormState => {
  const smtp = config?.smtp;
  const preferences = createDefaultPreferences();
  config?.preferences.forEach((pref) => {
    preferences[pref.trigger] = pref.enabled;
  });

  return {
    smtp: {
      host: smtp?.host ?? "",
      port: smtp?.port ?? 587,
      username: smtp?.username ?? "",
      password: "",
      from_email: smtp?.from_email ?? "",
      from_name: smtp?.from_name ?? "",
      use_tls: smtp?.use_tls ?? true,
      use_ssl: smtp?.use_ssl ?? false,
      has_password: smtp?.has_password ?? false,
      removePassword: false,
    },
    preferences,
  };
};

const buildUpdatePayload = (
  values: FormState,
): EmailNotificationConfigUpdate => {
  const smtp = values.smtp;
  const payload: EmailNotificationConfigUpdate = {
    smtp: {
      host: smtp.host.trim(),
      port: Number(smtp.port) || 587,
      username: smtp.username.trim() || null,
      use_tls: smtp.use_tls,
      use_ssl: smtp.use_ssl,
      from_email: smtp.from_email.trim(),
      from_name: smtp.from_name.trim() || null,
    },
    preferences: Object.entries(values.preferences).map(
      ([trigger, enabled]) => ({
        trigger: trigger as EmailNotificationTrigger,
        enabled,
      }),
    ),
  };

  const newPassword = smtp.password.trim();
  if (newPassword) {
    payload.smtp.password = newPassword;
  } else if (!smtp.has_password || smtp.removePassword) {
    payload.smtp.password = "";
  }

  return payload;
};

export const EmailNotificationsModal: FC = () => {
  const { isEditingEmailNotifications, onEditingEmailNotifications } =
    useDashboard();
  const { t } = useTranslation();
  const toast = useToast();

  const defaultValues = useMemo(() => mapConfigToForm(null), []);

  const form = useForm<FormState>({
    defaultValues,
  });

  const {
    data,
    isFetching,
    isLoading,
    refetch,
  } = useQuery<EmailNotificationConfig>(
    [QUERY_KEY],
    () => fetch<EmailNotificationConfig>("/email/notifications"),
    {
      enabled: isEditingEmailNotifications,
      refetchOnWindowFocus: false,
    },
  );

  useEffect(() => {
    if (isEditingEmailNotifications) {
      form.reset(mapConfigToForm(data ?? null));
    }
  }, [data, form, isEditingEmailNotifications]);

  const { mutateAsync, isLoading: isSaving } = useMutation(
    (payload: EmailNotificationConfigUpdate) =>
      fetch<EmailNotificationConfig>("/email/notifications", {
        method: "PUT",
        body: payload,
      }),
    {
      onSuccess: async (updated) => {
        toast({
          status: "success",
          title: t("emailNotifications.success"),
        });
        form.reset(mapConfigToForm(updated));
        await refetch();
      },
      onError: () => {
        toast({
          status: "error",
          title: t("emailNotifications.error"),
        });
      },
    },
  );

  const handleClose = () => {
    onEditingEmailNotifications(false);
  };

  const handleSubmit = form.handleSubmit(async (values) => {
    const payload = buildUpdatePayload(values);
    await mutateAsync(payload);
  });

  const loading = isLoading || (isFetching && !data);

  return (
    <Modal isOpen={isEditingEmailNotifications} onClose={handleClose} size="4xl">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(6px)" />
      <ModalContent mx={4}>
        <ModalHeader>{t("emailNotifications.title")}</ModalHeader>
        <ModalCloseButton disabled={isSaving} />
        <ModalBody>
          <VStack align="stretch" spacing={4}>
            <Text color="gray.600" _dark={{ color: "gray.300" }}>
              {t("emailNotifications.description")}
            </Text>
            {loading ? (
              <HStack justifyContent="center" py={10}>
                <Spinner />
              </HStack>
            ) : (
              <VStack align="stretch" spacing={6}>
                <Box>
                  <Text fontWeight="semibold" mb={2}>
                    {t("emailNotifications.smtp.title")}
                  </Text>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                    <FormControl isRequired>
                      <FormLabel>{t("emailNotifications.smtp.host")}</FormLabel>
                      <Input
                        size="sm"
                        disabled={isSaving}
                        error={
                          form.formState.errors.smtp?.host?.message as string
                        }
                        {...form.register("smtp.host", {
                          required: t("emailNotifications.errors.required"),
                        })}
                      />
                    </FormControl>
                    <FormControl isRequired>
                      <FormLabel>{t("emailNotifications.smtp.port")}</FormLabel>
                      <Controller
                        control={form.control}
                        name="smtp.port"
                        rules={{
                          required: t("emailNotifications.errors.required"),
                          min: {
                            value: 1,
                            message: t("emailNotifications.errors.port"),
                          },
                          max: {
                            value: 65535,
                            message: t("emailNotifications.errors.port"),
                          },
                        }}
                        render={({ field, fieldState }) => (
                          <Input
                            type="number"
                            size="sm"
                            disabled={isSaving}
                            value={String(field.value)}
                            min={1}
                            max={65535}
                            onChange={(value: any) =>
                              field.onChange(Number(value) || 0)
                            }
                            error={fieldState.error?.message}
                          />
                        )}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("emailNotifications.smtp.username")}</FormLabel>
                      <Input
                        size="sm"
                        disabled={isSaving}
                        {...form.register("smtp.username")}
                      />
                    </FormControl>
                    <FormControl isRequired>
                      <FormLabel>{t("emailNotifications.smtp.fromEmail")}</FormLabel>
                      <Input
                        size="sm"
                        type="email"
                        disabled={isSaving}
                        error={
                          form.formState.errors.smtp?.from_email?.message as string
                        }
                        {...form.register("smtp.from_email", {
                          required: t("emailNotifications.errors.required"),
                        })}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("emailNotifications.smtp.fromName")}</FormLabel>
                      <Input
                        size="sm"
                        disabled={isSaving}
                        {...form.register("smtp.from_name")}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel>{t("emailNotifications.smtp.password")}</FormLabel>
                      <Input
                        size="sm"
                        type="password"
                        disabled={isSaving}
                        {...form.register("smtp.password")}
                      />
                      <FormHelperText>
                        {t("emailNotifications.smtp.passwordHint")}
                      </FormHelperText>
                      {form.watch("smtp.has_password") && (
                        <Checkbox
                          mt={2}
                          size="sm"
                          isChecked={form.watch("smtp.removePassword")}
                          isDisabled={isSaving}
                          onChange={(event) =>
                            form.setValue(
                              "smtp.removePassword",
                              event.target.checked,
                            )
                          }
                        >
                          {t("emailNotifications.smtp.removePassword")}
                        </Checkbox>
                      )}
                    </FormControl>
                  </SimpleGrid>
                  <HStack spacing={6} mt={4} alignItems="center">
                    <Controller
                      control={form.control}
                      name="smtp.use_tls"
                      render={({ field }) => (
                        <FormControl display="flex" alignItems="center">
                          <Switch
                            isChecked={field.value}
                            onChange={(event) => {
                              field.onChange(event.target.checked);
                              if (event.target.checked) {
                                form.setValue("smtp.use_ssl", false);
                              }
                            }}
                            isDisabled={isSaving}
                          />
                          <FormLabel mb="0" ml={2}>
                            {t("emailNotifications.smtp.useTLS")}
                          </FormLabel>
                        </FormControl>
                      )}
                    />
                    <Controller
                      control={form.control}
                      name="smtp.use_ssl"
                      render={({ field }) => (
                        <FormControl display="flex" alignItems="center">
                          <Switch
                            isChecked={field.value}
                            onChange={(event) => {
                              field.onChange(event.target.checked);
                              if (event.target.checked) {
                                form.setValue("smtp.use_tls", false);
                              }
                            }}
                            isDisabled={isSaving}
                          />
                          <FormLabel mb="0" ml={2}>
                            {t("emailNotifications.smtp.useSSL")}
                          </FormLabel>
                        </FormControl>
                      )}
                    />
                  </HStack>
                </Box>

                <Divider />

                <Box>
                  <Text fontWeight="semibold" mb={2}>
                    {t("emailNotifications.preferences.title")}
                  </Text>
                  <Text fontSize="sm" color="gray.600" _dark={{ color: "gray.300" }} mb={3}>
                    {t("emailNotifications.preferences.description")}
                  </Text>
                  <VStack align="stretch" spacing={3}>
                    {TRIGGERS.map(({ key, label, description }) => (
                      <Controller
                        key={key}
                        control={form.control}
                        name={`preferences.${key}` as const}
                        render={({ field }) => (
                          <HStack align="flex-start" justifyContent="space-between">
                            <Box pr={4}>
                              <Text fontWeight="medium">
                                {t(label)}
                              </Text>
                              <Text fontSize="sm" color="gray.600" _dark={{ color: "gray.300" }}>
                                {t(description)}
                              </Text>
                            </Box>
                            <Switch
                              isChecked={field.value}
                              onChange={(event) => field.onChange(event.target.checked)}
                              isDisabled={isSaving}
                            />
                          </HStack>
                        )}
                      />
                    ))}
                  </VStack>
                </Box>
              </VStack>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter gap={2}>
          <Button variant="ghost" onClick={handleClose} disabled={isSaving}>
            {t("cancel")}
          </Button>
          <Button
            colorScheme="primary"
            onClick={handleSubmit}
            isLoading={isSaving}
          >
            {t("emailNotifications.save")}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default EmailNotificationsModal;
