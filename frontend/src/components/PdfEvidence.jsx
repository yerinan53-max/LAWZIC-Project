import { useEffect, useState } from "react";
import { apiBlob } from "../api/client";

export default function PdfEvidence({contractId, location}) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!contractId || !location?.page) return;
    let active = true;
    let objectUrl = "";
    apiBlob(`/contracts/${contractId}/pages/${location.page}`).then(blob => {
      objectUrl = URL.createObjectURL(blob);
      if (active) setUrl(objectUrl);
    });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [contractId, location?.page]);
  if (!location) return null;
  return <div className="pdf-evidence">
    <div className="pdf-page">
      {url && <img src={url} alt={`계약서 ${location.page}페이지`} />}
      {location.boxes?.map((box, index) => <span className="pdf-highlight" key={index} style={{
        left: `${box.x * 100}%`, top: `${box.y * 100}%`,
        width: `${box.width * 100}%`, height: `${box.height * 100}%`,
      }}/>)}
    </div>
    <small>{location.page}페이지 원문 위치</small>
  </div>;
}
