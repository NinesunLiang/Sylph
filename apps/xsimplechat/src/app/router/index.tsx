import { createBrowserRouter, Navigate } from "react-router-dom";
import { paths } from "@/router/paths";
import { ChatPage } from "@/pages/chat";
import { DiscoverPage } from "@/pages/discover";
import { AssistantPage } from "@/pages/assistant";
import { TranslationPage } from "@/pages/translation";
import { FilesPage } from "@/pages/files";
import { SettingsPage } from "@/pages/settings";
import { MemberPage } from "@/pages/member";

// 全量预注册路由（骨架期一次性完成；夜间禁止改 router —— 工作流契约）
export const router = createBrowserRouter([
  { path: paths.home, element: <Navigate to={paths.chat()} replace /> },
  { path: paths.chat(), element: <ChatPage /> },
  { path: paths.chat(":session"), element: <ChatPage /> },
  { path: paths.discover, element: <DiscoverPage /> },
  { path: paths.assistant(":slug"), element: <AssistantPage /> },
  { path: paths.translation, element: <TranslationPage /> },
  { path: paths.files, element: <FilesPage /> },
  { path: paths.settings, element: <SettingsPage /> },
  { path: paths.member, element: <MemberPage /> },
  { path: "*", element: <Navigate to={paths.chat()} replace /> },
]);
