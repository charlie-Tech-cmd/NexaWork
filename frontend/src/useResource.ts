import { useEffect, useEffectEvent, useState } from "react";
import { errorMessage } from "./api";
// Keys consist of route identifiers, never credentials. A changed key hides old
// data synchronously, before effects run, so a fast click cannot select stale rows.
export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  dependencies: unknown[],
) {
  const key = JSON.stringify(dependencies);
  const [result, setResult] = useState<{
    key: string;
    data: T | null;
    error: string;
    loading: boolean;
  } | null>(null);
  const [revision, setRevision] = useState(0);
  const fetchResource = useEffectEvent(load);
  useEffect(() => {
    const controller = new AbortController();
    setResult({ key, data: null, error: "", loading: true });
    fetchResource(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setResult({ key, data, error: "", loading: false });
      })
      .catch((cause) => {
        if (!controller.signal.aborted)
          setResult({
            key,
            data: null,
            error: errorMessage(cause),
            loading: false,
          });
      });
    return () => controller.abort();
  }, [key, revision]);
  const current = result?.key === key ? result : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? "",
    loading: current?.loading ?? true,
    reload: () => setRevision((value) => value + 1),
  };
}
