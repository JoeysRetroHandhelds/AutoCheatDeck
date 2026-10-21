import { ConfirmModal, DialogButton, Field, PanelSection, PanelSectionRow, showModal } from "@decky/ui";
import { type FC, useEffect, useState } from "react";
import { FaDownload, FaUndo } from "react-icons/fa";

import {
  checkPluginUpdate,
  installPluginUpdate,
  type PluginUpdateInfo,
  rollbackPluginUpdate,
  sendNotice,
} from "../infra/decky";
import { logger } from "../utils/logger";
import { t } from "../utils/translate";

export const PluginUpdate: FC = () => {
  const [info, setInfo] = useState<PluginUpdateInfo>();
  const [busy, setBusy] = useState(false);

  const check = async (notify: boolean) => {
    setBusy(true);
    try {
      const result = await checkPluginUpdate();
      setInfo(result);
      if (notify && !result.available) sendNotice(t("UPDATE_UP_TO_DATE"));
    } catch (e) {
      logger.error("Update check failed:", e);
      if (notify) sendNotice(t("UPDATE_CHECK_FAILED"));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    check(false);
  }, []);

  const install = () =>
    showModal(
      <ConfirmModal
        strTitle={`${t("UPDATE_INSTALL")} ${info?.latest}`}
        strDescription={info?.notes || t("UPDATE_RESTART_DESC")}
        strOKButtonText={t("UPDATE_INSTALL")}
        onOK={async () => {
          setBusy(true);
          sendNotice(t("UPDATE_INSTALLING"));
          try {
            await installPluginUpdate();
          } catch (e) {
            logger.error("Update failed:", e);
            sendNotice(`${t("UPDATE_FAILED")} ${e}`);
            setBusy(false);
          }
        }}
      />,
    );

  const rollback = () =>
    showModal(
      <ConfirmModal
        strTitle={t("UPDATE_ROLLBACK")}
        strDescription={t("UPDATE_RESTART_DESC")}
        onOK={() => rollbackPluginUpdate().catch((e) => sendNotice(`${t("UPDATE_FAILED")} ${e}`))}
      />,
    );

  return (
    <PanelSection title={t("UPDATE_TITLE")}>
      <PanelSectionRow>
        <Field
          label={info?.available ? `${t("UPDATE_AVAILABLE")} ${info.latest}` : t("UPDATE_VERSION")}
          description={info ? `${t("UPDATE_VERSION")} ${info.current}` : undefined}
          padding="standard"
          bottomSeparator="none"
          childrenLayout="below"
        >
          {info?.available ? (
            <DialogButton disabled={busy} onClick={install}>
              <FaDownload /> {t("UPDATE_INSTALL")}
            </DialogButton>
          ) : (
            <DialogButton disabled={busy} onClick={() => check(true)}>
              {t("UPDATE_CHECK")}
            </DialogButton>
          )}
        </Field>
      </PanelSectionRow>
      {info?.hasBackup && (
        <PanelSectionRow>
          <DialogButton disabled={busy} onClick={rollback}>
            <FaUndo /> {t("UPDATE_ROLLBACK")}
          </DialogButton>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
};
