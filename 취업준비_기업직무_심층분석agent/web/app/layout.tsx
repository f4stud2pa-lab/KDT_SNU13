import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "취업 준비 기업·직무 심층분석 에이전트",
  description: "기업명과 직무를 입력하면 실제 업무, 채용 이유, 필요 역량, 컬처핏, 자소서·면접 전략까지 16개 섹션으로 분석합니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-900">{children}</body>
    </html>
  );
}
