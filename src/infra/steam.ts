import type { AppDetails } from "@decky/ui/dist/globals/steam-client/App";

export const registerForAppDetails = (appid: number, onDetails: (details: AppDetails) => void) =>
  SteamClient.Apps.RegisterForAppDetails(appid, onDetails);

declare const appStore: { GetAppOverviewByAppID(appid: number): { display_name?: string } | null } | undefined;

export const getAppName = (appid: number): string => appStore?.GetAppOverviewByAppID(appid)?.display_name ?? "";

export const setAppLaunchOptions = (appid: number, options: string): void => {
  SteamClient.Apps.SetAppLaunchOptions(appid, options);
};
