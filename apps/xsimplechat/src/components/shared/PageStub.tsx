import { Empty, Typography } from "antd";

interface PageStubProps {
  title: string;
  hint?: string;
}

// 骨架期 stub：非本期页面（发现/详情/翻译/文件/设置/会员）占位，路由可达、可编译
export function PageStub({ title, hint }: PageStubProps) {
  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        background: "var(--ant-color-bg-layout)",
      }}
    >
      <Typography.Title level={4} style={{ margin: 0 }}>
        {title}
      </Typography.Title>
      <Typography.Text type="secondary">
        {hint ?? "页面骨架已注册，UI 还原排期后续夜次。"}
      </Typography.Text>
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 8 }} />
    </div>
  );
}
