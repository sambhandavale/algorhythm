"use client";

import React, { useState, useEffect, useMemo } from "react";
import striverData from "../data/striver_a2z.json";
import {
  ChevronDown,
  ChevronRight,
  Check,
  Search,
  ExternalLink,
  Video,
  FileText,
  Flame,
  CheckCircle2,
  RefreshCw,
  Sparkles,
} from "lucide-react";

interface Problem {
  id: string;
  order: number;
  title: string;
  step: number;
  stepTitle: string;
  topic: string;
  tier?: string;
  difficulty: string;
  platform: string;
  url: string;
  article?: string | null;
  video?: string | null;
  lcSlug?: string;
}

const problems: Problem[] = (striverData as any).problems || [];

export default function TrackerDashboard() {
  const [solvedIds, setSolvedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "solved" | "unsolved">("all");
  const [userProfile, setUserProfile] = useState<any>(null);

  // Accordion state
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({
    "Step 4: Binary Search": true,
  });
  const [expandedPatterns, setExpandedPatterns] = useState<Record<string, boolean>>({
    "Step 4: Binary Search-Fundamentals": true,
    "Step 4: Binary Search-On answers": true,
  });

  // Fetch initial progress from API
  useEffect(() => {
    async function fetchProgress() {
      try {
        const res = await fetch("/api/progress");
        const data = await res.json();
        if (data.solvedIds) {
          setSolvedIds(new Set([...data.solvedIds, ...(data.skippedIds || [])]));
        }
        if (data.user) {
          setUserProfile(data.user);
        }
      } catch (err) {
        console.error("Failed to load progress:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchProgress();
  }, []);

  // Toggle single problem
  const toggleProblem = async (problem: Problem) => {
    const isCurrentlySolved = solvedIds.has(problem.id);
    const newSolved = new Set(solvedIds);

    if (isCurrentlySolved) {
      newSolved.delete(problem.id);
    } else {
      newSolved.add(problem.id);
    }
    setSolvedIds(newSolved);

    try {
      await fetch("/api/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userProfile?.user_id || "",
          problem_id: problem.id,
          slug: problem.lcSlug || problem.id,
          status: isCurrentlySolved ? "UNSOLVED" : "SOLVED",
        }),
      });
    } catch (e) {
      console.error("Save error:", e);
    }
  };

  // Bulk toggle a pattern/section
  const bulkToggleSection = async (sectionProblems: Problem[], targetStatus: "SOLVED" | "UNSOLVED") => {
    setSaving(true);
    const newSolved = new Set(solvedIds);
    const pids = sectionProblems.map((p) => p.id);

    pids.forEach((pid) => {
      if (targetStatus === "SOLVED") newSolved.add(pid);
      else newSolved.delete(pid);
    });
    setSolvedIds(newSolved);

    try {
      await fetch("/api/progress/bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userProfile?.user_id || "",
          problem_ids: pids,
          status: targetStatus,
        }),
      });
    } catch (e) {
      console.error("Bulk error:", e);
    } finally {
      setSaving(false);
    }
  };

  // Organize problems hierarchically: Step -> Topic/Pattern -> Problems
  const hierarchy = useMemo(() => {
    const stepMap = new Map<string, { stepNum: number; stepTitle: string; patterns: Map<string, Problem[]> }>();

    problems.forEach((p) => {
      const stepKey = `Step ${p.step}: ${p.stepTitle}`;
      if (!stepMap.has(stepKey)) {
        stepMap.set(stepKey, {
          stepNum: p.step,
          stepTitle: p.stepTitle,
          patterns: new Map(),
        });
      }
      const patternMap = stepMap.get(stepKey)!.patterns;
      const patternKey = p.topic || "General";
      if (!patternMap.has(patternKey)) {
        patternMap.set(patternKey, []);
      }
      patternMap.get(patternKey)!.push(p);
    });

    return Array.from(stepMap.entries()).sort((a, b) => a[1].stepNum - b[1].stepNum);
  }, []);

  // Filtered views
  const filteredHierarchy = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return hierarchy
      .map(([stepKey, stepData]) => {
        const filteredPatterns = Array.from(stepData.patterns.entries())
          .map(([patKey, patProblems]) => {
            const matchingProblems = patProblems.filter((p) => {
              const matchesSearch =
                !query ||
                p.title.toLowerCase().includes(query) ||
                (p.lcSlug && p.lcSlug.toLowerCase().includes(query)) ||
                p.topic.toLowerCase().includes(query);

              const isSolved = solvedIds.has(p.id);
              const matchesFilter =
                filter === "all" ||
                (filter === "solved" && isSolved) ||
                (filter === "unsolved" && !isSolved);

              return matchesSearch && matchesFilter;
            });

            return [patKey, matchingProblems] as [string, Problem[]];
          })
          .filter(([_, probs]) => probs.length > 0);

        return {
          stepKey,
          stepNum: stepData.stepNum,
          stepTitle: stepData.stepTitle,
          patterns: filteredPatterns,
          totalOriginal: Array.from(stepData.patterns.values()).flat().length,
        };
      })
      .filter((step) => step.patterns.length > 0);
  }, [hierarchy, searchQuery, filter, solvedIds]);

  const totalProblems = problems.length;
  const totalSolved = problems.filter((p) => solvedIds.has(p.id)).length;
  const overallPct = Math.round((totalSolved / totalProblems) * 100);

  return (
    <div className="min-h-screen bg-[#0D0F17] text-slate-200">
      {/* Top Navbar */}
      <header className="sticky top-0 z-40 bg-[#0F121C]/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-4">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
              DSA
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Striver's A2Z Tracker
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Cloud Synced
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Connected to Discord Bot & LeetCode:{" "}
                <span className="text-slate-200 font-medium">{userProfile?.leetcode_username || "magneto069"}</span>
              </p>
            </div>
          </div>

          {/* Stats Badges */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#151928] border border-slate-800">
              <Flame className="w-4 h-4 text-orange-500 fill-orange-500" />
              <span className="text-sm font-semibold text-slate-200">
                {userProfile?.current_streak || 1} Day Streak
              </span>
            </div>

            <div className="flex items-center gap-3 px-4 py-1.5 rounded-lg bg-[#151928] border border-slate-800">
              <div className="text-right">
                <div className="text-sm font-bold text-white">
                  {totalSolved} / {totalProblems}
                </div>
                <div className="text-xs text-slate-400">{overallPct}% Completed</div>
              </div>
              <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500"
                  style={{ width: `${overallPct}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-4 md:px-6 py-8">
        {/* Search & Filter Toolbar */}
        <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-[#131622] p-3 rounded-xl border border-slate-800">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search problem, pattern, or slug..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D0F17] border border-slate-700/80 rounded-lg pl-9 pr-3 py-1.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="flex bg-[#0D0F17] p-1 rounded-lg border border-slate-800 text-xs font-medium">
              {(["all", "unsolved", "solved"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setFilter(mode)}
                  className={`px-3 py-1 rounded capitalize transition-all ${
                    filter === mode ? "bg-blue-600 text-white font-semibold" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>

            <button
              onClick={() => {
                const allExpanded = Object.values(expandedSteps).every(Boolean);
                const nextState = !allExpanded;
                const newSteps: Record<string, boolean> = {};
                const newPatterns: Record<string, boolean> = {};
                hierarchy.forEach(([sKey, sData]) => {
                  newSteps[sKey] = nextState;
                  Array.from(sData.patterns.keys()).forEach((pKey) => {
                    newPatterns[`${sKey}-${pKey}`] = nextState;
                  });
                });
                setExpandedSteps(newSteps);
                setExpandedPatterns(newPatterns);
              }}
              className="px-3 py-1.5 rounded-lg bg-[#0D0F17] border border-slate-800 hover:bg-slate-800 text-xs text-slate-300 font-medium transition"
            >
              Toggle All
            </button>
          </div>
        </div>

        {/* Step Accordion List */}
        <div className="space-y-4">
          {filteredHierarchy.map((step) => {
            const isStepExpanded = !!expandedSteps[step.stepKey];
            const allStepProblems = hierarchy.find(([k]) => k === step.stepKey)?.[1].patterns
              ? Array.from(hierarchy.find(([k]) => k === step.stepKey)![1].patterns.values()).flat()
              : [];
            const stepSolved = allStepProblems.filter((p) => solvedIds.has(p.id)).length;
            const stepTotal = allStepProblems.length;
            const stepPct = stepTotal ? Math.round((stepSolved / stepTotal) * 100) : 0;
            const isStepComplete = stepSolved === stepTotal && stepTotal > 0;

            return (
              <div
                key={step.stepKey}
                className="bg-[#121520] border border-slate-800/80 rounded-xl overflow-hidden transition-all shadow-sm"
              >
                {/* Step Header */}
                <div
                  onClick={() =>
                    setExpandedSteps((prev) => ({ ...prev, [step.stepKey]: !prev[step.stepKey] }))
                  }
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-[#161a29] transition select-none"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400">
                      {isStepExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </span>
                    <h2 className="text-base font-semibold text-white tracking-wide">
                      {step.stepTitle}
                    </h2>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Step Progress Bar */}
                    <div className="hidden sm:flex items-center gap-3">
                      <div className="w-28 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${stepPct}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400 font-medium w-12 text-right">
                        {stepSolved}/{stepTotal}
                      </span>
                    </div>

                    {/* Step Bulk Done button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        bulkToggleSection(allStepProblems, isStepComplete ? "UNSOLVED" : "SOLVED");
                      }}
                      className={`text-xs px-2.5 py-1 rounded-md border font-medium transition ${
                        isStepComplete
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
                          : "bg-slate-800/60 text-slate-300 border-slate-700 hover:bg-slate-700/60"
                      }`}
                    >
                      {isStepComplete ? "✓ Completed" : "Mark Step Done"}
                    </button>
                  </div>
                </div>

                {/* Patterns inside this step */}
                {isStepExpanded && (
                  <div className="border-t border-slate-800/60 bg-[#0F121C] p-3 space-y-3">
                    {step.patterns.map(([patternKey, patternProblems]) => {
                      const fullPatKey = `${step.stepKey}-${patternKey}`;
                      const isPatExpanded = expandedPatterns[fullPatKey] ?? true;

                      const patSolved = patternProblems.filter((p) => solvedIds.has(p.id)).length;
                      const patTotal = patternProblems.length;
                      const patPct = patTotal ? Math.round((patSolved / patTotal) * 100) : 0;
                      const isPatComplete = patSolved === patTotal && patTotal > 0;

                      return (
                        <div
                          key={fullPatKey}
                          className="bg-[#141724] border border-slate-800/70 rounded-lg overflow-hidden"
                        >
                          {/* Pattern Sub-Header */}
                          <div
                            onClick={() =>
                              setExpandedPatterns((prev) => ({
                                ...prev,
                                [fullPatKey]: !(prev[fullPatKey] ?? true),
                              }))
                            }
                            className="flex items-center justify-between px-3.5 py-2.5 cursor-pointer hover:bg-[#181c2c] transition select-none"
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-slate-400">
                                {isPatExpanded ? (
                                  <ChevronDown className="w-4 h-4" />
                                ) : (
                                  <ChevronRight className="w-4 h-4" />
                                )}
                              </span>
                              <h3 className="text-sm font-medium text-slate-200">{patternKey}</h3>
                            </div>

                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-2 text-xs text-slate-400">
                                <div className="w-16 h-1 bg-slate-800 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 transition-all duration-300"
                                    style={{ width: `${patPct}%` }}
                                  />
                                </div>
                                <span>
                                  {patSolved}/{patTotal}
                                </span>
                              </div>

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  bulkToggleSection(patternProblems, isPatComplete ? "UNSOLVED" : "SOLVED");
                                }}
                                className={`text-[11px] px-2 py-0.5 rounded border transition ${
                                  isPatComplete
                                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                    : "bg-slate-800/60 text-slate-400 border-slate-700/60 hover:text-white"
                                }`}
                              >
                                {isPatComplete ? "✓ All Done" : "Mark Section"}
                              </button>
                            </div>
                          </div>

                          {/* Problem Rows */}
                          {isPatExpanded && (
                            <div className="divide-y divide-slate-800/50 bg-[#10131F]">
                              {patternProblems.map((prob) => {
                                const isSolved = solvedIds.has(prob.id);

                                return (
                                  <div
                                    key={prob.id}
                                    className={`flex items-center justify-between px-4 py-2.5 hover:bg-[#151928] transition group ${
                                      isSolved ? "bg-emerald-500/[0.02]" : ""
                                    }`}
                                  >
                                    {/* Left: Checkbox & Title */}
                                    <div className="flex items-center gap-3 min-w-0 pr-4">
                                      <button
                                        onClick={() => toggleProblem(prob)}
                                        className={`w-5 h-5 rounded flex items-center justify-center transition-all ${
                                          isSolved
                                            ? "bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/30"
                                            : "border border-slate-700 hover:border-slate-500 bg-[#0D0F17]"
                                        }`}
                                      >
                                        {isSolved && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                                      </button>

                                      <div className="flex items-center gap-2 truncate">
                                        <a
                                          href={prob.url}
                                          target="_blank"
                                          rel="noreferrer"
                                          className={`text-sm font-normal truncate hover:underline ${
                                            isSolved ? "text-slate-400 line-through" : "text-slate-100 hover:text-blue-400"
                                          }`}
                                        >
                                          {prob.title}
                                        </a>

                                        {/* Tier / Difficulty Badge */}
                                        {prob.tier && (
                                          <span
                                            className={`text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded border ${
                                              prob.tier === "basic"
                                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                                : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                            }`}
                                          >
                                            {prob.tier}
                                          </span>
                                        )}

                                        <span
                                          className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                                            prob.difficulty.toLowerCase() === "easy"
                                              ? "text-emerald-400"
                                              : prob.difficulty.toLowerCase() === "hard"
                                              ? "text-red-400"
                                              : "text-amber-400"
                                          }`}
                                        >
                                          {prob.difficulty}
                                        </span>
                                      </div>
                                    </div>

                                    {/* Right: Quick action icons */}
                                    <div className="flex items-center gap-3 shrink-0 text-slate-400">
                                      {prob.video && (
                                        <a
                                          href={prob.video}
                                          target="_blank"
                                          rel="noreferrer"
                                          title="Watch Video Solution"
                                          className="hover:text-red-400 transition"
                                        >
                                          <Video className="w-4 h-4" />
                                        </a>
                                      )}
                                      {prob.article && (
                                        <a
                                          href={prob.article}
                                          target="_blank"
                                          rel="noreferrer"
                                          title="Read Striver Article"
                                          className="hover:text-blue-400 transition"
                                        >
                                          <FileText className="w-4 h-4" />
                                        </a>
                                      )}
                                      {prob.url && (
                                        <a
                                          href={prob.url}
                                          target="_blank"
                                          rel="noreferrer"
                                          title="Solve on Platform"
                                          className="hover:text-white transition"
                                        >
                                          <ExternalLink className="w-4 h-4" />
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
