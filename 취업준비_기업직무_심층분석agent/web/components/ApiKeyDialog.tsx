"use client";

import { useState } from "react";
import { EFFORT_OPTIONS, MODEL_OPTIONS } from "@/lib/agents";

type Props = {
  initialKey: string;
  initialModel: string;
  initialEffort: string;
  onSave: (key: string, model: string, effort: string) => void;
  onClose: () => void;
};

export default function ApiKeyDialog({ initialKey, initialModel, initialEffort, onSave, onClose }: Props) {
  const [key, setKey] = useState(initialKey);
  const [model, setModel] = useState(initialModel);
  const [effort, setEffort] = useState(initialEffort);
  const isPreset = MODEL_OPTIONS.some((m) => m.id === model);
  const [custom, setCustom] = useState(!isPreset);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold">OpenAI API 키 / 모델 설정</h2>

        <label className="mt-4 block text-sm font-medium">API 키</label>
        <input
          type="password"
          autoComplete="off"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="sk-..."
          className="input mt-1 font-mono"
        />
        <ul className="mt-2 space-y-1 text-xs text-slate-600">
          <li>키는 이 브라우저(localStorage)에만 저장되고, 분석 요청 때만 서버를 거쳐 OpenAI로 전달됩니다. 서버는 키를 저장하거나 기록하지 않습니다.</li>
          <li>
            키 발급:{" "}
            <a className="text-blue-600 underline" href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer">
              platform.openai.com/api-keys
            </a>
            . 사용 요금은 이 키의 OpenAI 계정에 청구됩니다.
          </li>
          <li>분석 1회에 약 10~13번의 모델 호출과 여러 번의 웹 검색이 발생합니다. 정확한 비용은 OpenAI 사용량 페이지에서 확인하세요.</li>
          <li>공용 PC라면 사용 후 &lsquo;키 삭제&rsquo;를 눌러 주세요.</li>
        </ul>

        <label className="mt-5 block text-sm font-medium">모델</label>
        <select
          className="input mt-1"
          value={custom ? "__custom" : model}
          onChange={(e) => {
            if (e.target.value === "__custom") {
              setCustom(true);
            } else {
              setCustom(false);
              setModel(e.target.value);
            }
          }}
        >
          {MODEL_OPTIONS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
          <option value="__custom">직접 입력</option>
        </select>
        {custom && (
          <input
            className="input mt-2 font-mono"
            value={model}
            onChange={(e) => setModel(e.target.value.trim())}
            placeholder="예: gpt-5.4-mini"
          />
        )}

        <label className="mt-4 block text-sm font-medium">추론 강도 (reasoning effort)</label>
        <select className="input mt-1" value={effort} onChange={(e) => setEffort(e.target.value)}>
          {EFFORT_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>

        <div className="mt-6 flex items-center justify-between">
          <button
            type="button"
            className="btn-ghost text-rose-600"
            onClick={() => {
              setKey("");
              onSave("", model, effort);
            }}
          >
            키 삭제
          </button>
          <div className="flex gap-2">
            <button type="button" className="btn-ghost" onClick={onClose}>
              취소
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!model}
              onClick={() => onSave(key.trim(), model, effort)}
            >
              저장
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
