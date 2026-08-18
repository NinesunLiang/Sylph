import { useParams } from "react-router-dom";
import { PageStub } from "@/components/shared/PageStub";

export function AssistantPage() {
  const { slug } = useParams<{ slug: string }>();
  return <PageStub title="助手详情" hint={`slug: ${slug ?? "-"}`} />;
}
