import { ConfirmModal, DialogButton, Field, Focusable, showModal } from "@decky/ui";
import { type FC, useEffect, useState } from "react";
import { FaGlobe, FaWindowRestore } from "react-icons/fa";

import { type DropdownPreset, LaunchOptionsPreview, ToggleDropdown, ToggleFilePicker } from "../components";
import { LangCodes } from "../data/languageCodes.json";
import { language, sidecarProgram } from "../domain/features";
import { useOptions } from "../hooks";
import {
  browseFiles,
  downloadTrainer,
  getHomePath,
  getInstalledTrainer,
  type InstalledTrainer,
  listTrainerVersions,
  sendNotice,
} from "../infra/decky";
import { getAppName } from "../infra/steam";
import { FindTrainer } from "../modals";
import { t } from "../utils/translate";

const Normal: FC = () => {
  const { appid, options, editable, applyEdit } = useOptions();
  const [showSidecar, setShowSidecar] = useState(sidecarProgram.isEnabled(options));
  const [showLang, setShowLang] = useState(language.isEnabled(options));
  const [installed, setInstalled] = useState<InstalledTrainer | null>(null);

  useEffect(() => {
    getInstalledTrainer(appid).then(setInstalled, () => setInstalled(null));
  }, [appid]);

  const setSidecarPath = (path: string) => {
    const result = sidecarProgram.set(options, path);
    if (!result.ok || !applyEdit(result)) setShowSidecar(false);
  };

  const onTrainerInstalled = (path: string) => {
    setSidecarPath(path);
    getInstalledTrainer(appid).then(setInstalled, () => {});
    sendNotice(t("TRAINER_INSTALLED"));
  };

  const handleFindTrainer = () => {
    showModal(<FindTrainer appid={appid} gameName={getAppName(appid)} onInstalled={onTrainerInstalled} />);
  };

  const handleCheckUpdate = async () => {
    if (!installed) return;
    const latest = (await listTrainerVersions(installed.pageUrl)).versions[0];
    if (!latest || latest.title === installed.title) {
      sendNotice(t("TRAINER_UP_TO_DATE"));
      return;
    }
    showModal(
      <ConfirmModal
        strTitle={t("TRAINER_UPDATE_AVAILABLE")}
        strDescription={latest.title}
        strOKButtonText={t("TRAINER_DOWNLOAD")}
        onOK={async () => {
          const result = await downloadTrainer({
            appid,
            url: latest.url,
            pageUrl: installed.pageUrl,
            title: latest.title,
          });
          onTrainerInstalled(result.path);
        }}
      />,
    );
  };

  const handleSidecarBrowse = async () => {
    const defaultPath = sidecarProgram.directory(options) ?? (await getHomePath());
    const filePickerRes = await browseFiles(defaultPath, true, ["exe", "bat"]);
    setSidecarPath(filePickerRes.path);
  };

  return (
    <Focusable style={{ display: "flex", flexDirection: "column" }}>
      <LaunchOptionsPreview />

      <ToggleFilePicker
        label={t("NORMAL_SIDECAR_TOGGLE_LABEL")}
        description={t("NORMAL_SIDECAR_TOGGLE_DESC")}
        icon={<FaWindowRestore />}
        disabled={!editable}
        checked={showSidecar || sidecarProgram.isEnabled(options)}
        onToggle={(enable: boolean) => {
          if (enable) {
            setShowSidecar(true);
            return;
          }
          const result = sidecarProgram.disable(options);
          if (result.ok && applyEdit(result)) setShowSidecar(false);
        }}
        value={sidecarProgram.path(options)}
        onBrowse={handleSidecarBrowse}
      />

      {(showSidecar || sidecarProgram.isEnabled(options)) && (
        <Field bottomSeparator="standard" childrenLayout="below">
          <Focusable style={{ display: "flex", gap: "8px" }}>
            <DialogButton disabled={!editable} onClick={handleFindTrainer}>
              {t("TRAINER_FIND")}
            </DialogButton>
            {installed && (
              <DialogButton disabled={!editable} onClick={handleCheckUpdate}>
                {t("TRAINER_CHECK_UPDATE")}
              </DialogButton>
            )}
          </Focusable>
        </Field>
      )}

      <ToggleDropdown
        label={t("NORMAL_LANG_TOGGLE_LABEL")}
        description={t("NORMAL_LANG_TOGGLE_DESC")}
        icon={<FaGlobe />}
        disabled={!editable}
        checked={showLang || language.isEnabled(options)}
        onToggle={(enable: boolean) => {
          if (enable) {
            setShowLang(true);
            return;
          }
          const result = language.disable(options);
          if (result.ok && applyEdit(result)) setShowLang(false);
        }}
        fieldLabel={t("NORMAL_LANG_LABEL")}
        value={language.value(options)}
        onInput={(value: string) => {
          const result = language.set(options, value);
          if (!result.ok || !applyEdit(result)) setShowLang(false);
        }}
        preset={LangCodes as DropdownPreset[]}
      />
    </Focusable>
  );
};

export default Normal;
