import { ConfirmModal, DialogButton, Focusable, ModalRoot, Spinner, TextField } from "@decky/ui";
import { type FC, useEffect, useState } from "react";

import {
  downloadTrainer,
  listTrainerVersions,
  searchTrainers,
  type TrainerLink,
  type TrainerPage,
} from "../infra/decky";
import { logger } from "../utils/logger";
import { t } from "../utils/translate";

type Step =
  | { kind: "results"; results: TrainerLink[] }
  | { kind: "versions"; page: TrainerLink; detail: TrainerPage }
  | { kind: "confirm"; page: TrainerLink; version: TrainerLink };

const listStyle = { display: "flex", flexDirection: "column", gap: "6px", marginTop: "12px" } as const;

export const FindTrainer: FC<{
  closeModal?: () => void;
  appid: number;
  gameName: string;
  onInstalled: (path: string) => void;
}> = ({ closeModal = () => {}, appid, gameName, onInstalled }) => {
  const [query, setQuery] = useState(gameName);
  const [step, setStep] = useState<Step>({ kind: "results", results: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(undefined);
    try {
      await action();
    } catch (e) {
      logger.error("Trainer lookup failed:", e);
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const doSearch = () => run(async () => setStep({ kind: "results", results: await searchTrainers(query) }));

  const openPage = (page: TrainerLink) =>
    run(async () => setStep({ kind: "versions", page, detail: await listTrainerVersions(page.url) }));

  const install = (page: TrainerLink, version: TrainerLink) =>
    run(async () => {
      const result = await downloadTrainer({ appid, url: version.url, pageUrl: page.url, title: version.title });
      onInstalled(result.path);
      closeModal();
    });

  useEffect(() => {
    if (gameName) doSearch();
  }, []);

  if (step.kind === "confirm") {
    return (
      <ConfirmModal
        strTitle={t("TRAINER_CONFIRM_TITLE")}
        strDescription={`${step.version.title}\n\n${t("TRAINER_CONFIRM_DESC")}`}
        strOKButtonText={busy ? t("TRAINER_DOWNLOADING") : t("TRAINER_DOWNLOAD")}
        bOKDisabled={busy}
        onOK={() => install(step.page, step.version)}
        onCancel={() => setStep({ kind: "results", results: [] })}
        closeModal={closeModal}
      />
    );
  }

  return (
    <ModalRoot closeModal={closeModal}>
      <Focusable style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <div style={{ flex: 1 }}>
          <TextField value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <DialogButton style={{ width: "auto" }} disabled={busy || !query} onClick={doSearch}>
          {t("TRAINER_SEARCH")}
        </DialogButton>
      </Focusable>

      {busy && <Spinner style={{ height: "32px", marginTop: "12px" }} />}
      {error && <div style={{ color: "#ff6b6b", marginTop: "12px" }}>{error}</div>}

      {!busy && step.kind === "results" && (
        <Focusable style={listStyle}>
          {step.results.length === 0 && <div>{t("TRAINER_NO_RESULTS")}</div>}
          {step.results.map((page) => (
            <DialogButton key={page.url} onClick={() => openPage(page)}>
              {page.title}
            </DialogButton>
          ))}
        </Focusable>
      )}

      {!busy && step.kind === "versions" && (
        <Focusable style={listStyle}>
          <div>
            {step.page.title}
            {step.detail.lastUpdated && ` · ${t("TRAINER_UPDATED")} ${step.detail.lastUpdated}`}
          </div>
          {step.detail.versions.length === 0 && <div>{t("TRAINER_NO_RESULTS")}</div>}
          {step.detail.versions.map((version) => (
            <DialogButton key={version.url} onClick={() => setStep({ kind: "confirm", page: step.page, version })}>
              {version.title}
            </DialogButton>
          ))}
        </Focusable>
      )}
    </ModalRoot>
  );
};
