import { useState } from "react";
import { Check, MagnifyingGlass, ShareNetwork } from "@phosphor-icons/react";
import { Button, Modal, Notice, ProfileIdentity } from "./primitives";

export function ShareDialog({
  onClose,
  notify,
}: {
  onClose: () => void;
  notify: (message: string) => void;
}) {
  const [query, setQuery] = useState(""),
    [searched, setSearched] = useState(false),
    [shared, setShared] = useState(false),
    [scope, setScope] = useState("heart");
  const match = query.trim().replace(/^@/, "").toLowerCase() === "wintercedar";
  return (
    <Modal title="Share with someone" onClose={onClose}>
      <p>
        Find someone by their exact handle. Their email and private recordings
        stay hidden.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearched(true);
        }}
      >
        <label className="sf-field">
          <span>Share with @username</span>
          <div className="sf-input-action">
            <input
              autoFocus
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSearched(false);
                setShared(false);
              }}
              placeholder="@wintercedar"
              autoComplete="off"
              maxLength={21}
            />
            <Button variant="secondary" type="submit">
              <MagnifyingGlass size={18} />
              Find
            </Button>
          </div>
          <small>Try @wintercedar in this closed, synthetic preview.</small>
        </label>
      </form>
      {searched &&
        (match ? (
          <div className="sf-share-match">
            <ProfileIdentity name="Maya Rahman" handle="wintercedar" />
            <label className="sf-field">
              <span>What can they access?</span>
              <select
                value={scope}
                onChange={(e) => {
                  setScope(e.target.value);
                  setShared(false);
                }}
              >
                <option value="heart">Heart audio only</option>
                <option value="lung">Lung audio only</option>
                <option value="result">Result details only</option>
                <option value="recording">Recording and all audio</option>
              </select>
            </label>
            <p className="sf-subtle">
              {scope === "heart"
                ? "Original, lung audio and result details remain restricted."
                : scope === "lung"
                  ? "Original, heart audio and result details remain restricted."
                  : scope === "result"
                    ? "Audio remains restricted. Result details do not grant sibling audio access."
                    : "This whole-recording grant includes the original and separated audio."}
            </p>
            <Button
              onClick={() => {
                setShared(true);
                notify(
                  "Local sharing state previewed. No real grant was created.",
                );
              }}
            >
              {shared ? <Check size={18} /> : <ShareNetwork size={18} />}{" "}
              {shared ? "Sharing previewed" : "Preview sharing"}
            </Button>
            {shared && (
              <Button
                variant="danger"
                onClick={() => {
                  setShared(false);
                  notify(
                    "Local revocation state previewed. No backend grant was changed.",
                  );
                }}
              >
                Revoke preview access
              </Button>
            )}
          </div>
        ) : (
          <Notice>No matching handle. Check the spelling and try again.</Notice>
        ))}
      <Notice>
        This prototype does not search production accounts or create grants. The
        existing backend remains authoritative for each exact resource.
      </Notice>
    </Modal>
  );
}
