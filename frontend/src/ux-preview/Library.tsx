import { useMemo, useState } from "react";
import {
  CaretLeft,
  CaretRight,
  MagnifyingGlass,
  Plus,
  Waveform,
  X,
} from "@phosphor-icons/react";
import { Button, GlassPanel, Segments } from "./primitives";
import { recordings } from "./domain";
import { RecordingList } from "./RecordingList";

type Filter = "all" | "ready" | "processing" | "shared";
export function Library({ onNew }: { onNew: () => void }) {
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState<Filter>("all"),
    [sort, setSort] = useState("newest"),
    [page, setPage] = useState(0);
  const rows = useMemo(() => {
    const items = recordings.filter(
      (r) =>
        (filter === "all" ||
          (filter === "shared" && r.shared) ||
          r.status === filter) &&
        `${r.title} ${r.publicId}`
          .toLowerCase()
          .includes(search.toLowerCase().trim()),
    );
    return sort === "newest" ? items : items.slice().reverse();
  }, [search, filter, sort]);
  return (
    <>
      <header className="sf-page-heading">
        <div>
          <h1>Your sound library</h1>
          <p>One place for recordings, from capture to review.</p>
        </div>
        <Button onClick={onNew}>
          <Plus size={20} />
          New recording
        </Button>
      </header>
      <GlassPanel className="sf-library-panel">
        <div className="sf-library-tools">
          <label className="sf-search-field">
            <MagnifyingGlass size={20} />
            <span className="sf-sr">
              Search by recording title or public ID
            </span>
            <input
              id="library-search"
              type="search"
              placeholder="Search by title or REC-ID"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
            {search && (
              <Button
                variant="icon"
                aria-label="Clear search"
                onClick={() => {
                  setSearch("");
                  setPage(0);
                }}
              >
                <X size={18} />
              </Button>
            )}
          </label>
          <label className="sf-sort">
            <span className="sf-sr">Sort recordings</span>
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(0);
              }}
            >
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>
        <div className="sf-library-filters">
          <Segments<Filter>
            label="Library filters"
            value={filter}
            onChange={(value) => {
              setFilter(value);
              setPage(0);
            }}
            items={[
              { id: "all", label: "All", count: recordings.length },
              { id: "ready", label: "Ready", count: 5 },
              { id: "processing", label: "Processing", count: 1 },
              { id: "shared", label: "Shared", count: 2 },
            ]}
          />
          <span>All recordings stay private by default.</span>
        </div>
        {rows.length ? (
          <RecordingList items={rows.slice(page * 6, page * 6 + 6)} />
        ) : (
          <div className="sf-empty">
            <Waveform size={38} />
            <h2>No recordings found</h2>
            <p>Try another title or recording ID, or clear the filter.</p>
            <Button
              variant="secondary"
              onClick={() => {
                setSearch("");
                setFilter("all");
                setPage(0);
              }}
            >
              Show all recordings
            </Button>
          </div>
        )}
        <div className="sf-library-footer">
          <span role="status">
            {rows.length > 6
              ? `${page * 6 + 1}–${Math.min(page * 6 + 6, rows.length)} of `
              : ""}
            {rows.length} {rows.length === 1 ? "recording" : "recordings"}
          </span>
          {rows.length > 6 ? (
            <nav className="sf-pagination" aria-label="Library pages">
              <Button
                variant="icon"
                aria-label="Previous page"
                disabled={page === 0}
                onClick={() => setPage((value) => value - 1)}
              >
                <CaretLeft size={18} />
              </Button>
              <Button
                variant="icon"
                aria-label="Next page"
                disabled={(page + 1) * 6 >= rows.length}
                onClick={() => setPage((value) => value + 1)}
              >
                <CaretRight size={18} />
              </Button>
            </nav>
          ) : (
            <p>One recording, one place.</p>
          )}
        </div>
      </GlassPanel>
      <div className="sf-library-bottom">
        <span>WAV audio · up to 25 MiB per upload</span>
        <p>Only people you explicitly share with can access your recordings.</p>
      </div>
    </>
  );
}
