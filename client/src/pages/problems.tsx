import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Filter,
  X,
  ChevronDown,
  Users,
  Building2,
  Tag,
  Dumbbell,
  CheckCircle,
} from "lucide-react";
import { CompanyLogo } from "@/components/CompanyLogo";
import { DifficultyBadge } from "@/components/DifficultyBadge";
import { Link } from "wouter";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { problemsApi } from "@/lib/auth";
import { useAuth } from "@/hooks/use-auth";

interface Problem {
  id: string;
  title: string;
  question: {
    description: string;
    tables: any[];
    expectedOutput: any[];
  };
  difficulty: string;
  tags: string[];
  company?: string | null;
  solvedCount: number;
  isUserSolved: boolean;
}

interface FilterState {
  difficulties: string[];
  companies: string[];
  tags: string[];
  status: "all" | "solved" | "unsolved";
}

export default function Problems() {
  const { user } = useAuth();
  const [location] = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<FilterState>({
    difficulties: [],
    companies: [],
    tags: [],
    status: "all",
  });

  // Handle URL search parameters for filtering
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const difficultyParam = urlParams.get('difficulty');
    const companyParam = urlParams.get('company');
    
    if (difficultyParam || companyParam) {
      setFilters(prev => ({
        ...prev,
        difficulties: difficultyParam ? [difficultyParam] : prev.difficulties,
        companies: companyParam ? [companyParam] : prev.companies,
      }));
    }
  }, [location]);

  const { data: problems, isLoading } = useQuery<Problem[]>({
    queryKey: ["/api/problems"],
    queryFn: () => problemsApi.getAll(),
  });

  // Get unique values for filter options
  const allCompanies = Array.from(
    new Set((problems ?? []).map((p) => p.company).filter(Boolean))
  ).sort();
  const allTags = Array.from(
    new Set((problems ?? []).flatMap((p) => p.tags || []))
  ).sort();
  // Normalize difficulties to handle case/whitespace differences
  const difficulties = Array.from(
    new Map(
      (problems ?? [])
        .map((p) => p.difficulty)
        .filter(Boolean)
        .map((d) => [d.trim().toLowerCase(), d.trim()])
    ).values()
  ).sort();

  // Get tag counts for display
  const getTagCount = (tag: string) => {
    return problems?.filter((p) => p.tags?.includes(tag)).length || 0;
  };

  // Filter problems based on all criteria
  const filteredProblems =
    problems?.filter((problem) => {
      // Search filter
      const matchesSearch =
        searchQuery === "" ||
        problem.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        problem.question.description.toLowerCase().includes(searchQuery.toLowerCase());

      // Difficulty filter (case-insensitive comparison)
      const matchesDifficulty =
        filters.difficulties.length === 0 ||
        filters.difficulties.some(filterDiff => 
          filterDiff.trim().toLowerCase() === problem.difficulty?.trim().toLowerCase()
        );

      // Company filter
      const matchesCompany =
        filters.companies.length === 0 ||
        (problem.company && filters.companies.includes(problem.company));

      // Tags filter - must have ALL selected tags (AND logic)
      const matchesTags =
        filters.tags.length === 0 ||
        filters.tags.every((tag) => problem.tags?.includes(tag));

      // Status filter - check if user has solved the problem
      const matchesStatus =
        filters.status === "all" ||
        (filters.status === "solved" && problem.isUserSolved === true) ||
        (filters.status === "unsolved" && problem.isUserSolved !== true);

      return (
        matchesSearch &&
        matchesDifficulty &&
        matchesCompany &&
        matchesTags &&
        matchesStatus
      );
    }) || [];


  const updateFilter = (key: keyof FilterState, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const toggleArrayFilter = (
    key: "difficulties" | "companies" | "tags",
    value: string
  ) => {
    setFilters((prev) => ({
      ...prev,
      [key]: prev[key].includes(value)
        ? prev[key].filter((item) => item !== value)
        : [...prev[key], value],
    }));
  };

  const clearFilters = () => {
    setFilters({
      difficulties: [],
      companies: [],
      tags: [],
      status: "all",
    });
    setSearchQuery("");
  };

  const getActiveFilterCount = () => {
    return (
      filters.difficulties.length +
      filters.companies.length +
      filters.tags.length +
      (filters.status !== "all" ? 1 : 0)
    );
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            SQL Practice Problems
          </h1>
          <p className="text-xl text-gray-600">
            Master SQL for interviews and professional development
          </p>
        </div>

        {/* Search and Filters */}
        <div className="mb-8 space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              placeholder="Search problems by title or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 h-12 text-lg border-gray-200 focus:border-orange-500 focus:ring-orange-500"
              data-testid="input-search-problems"
            />
          </div>

          {/* Filter Section */}
          <div className="flex flex-wrap gap-3 items-center">
            {/* Difficulty Filter */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="h-10 border-gray-200 hover:border-orange-500"
                  data-testid="button-difficulty-filter"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Difficulty
                  {filters.difficulties.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="ml-2 bg-orange-100 text-orange-700"
                    >
                      {filters.difficulties.length}
                    </Badge>
                  )}
                  <ChevronDown className="w-4 h-4 ml-2" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-64" align="start">
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900">
                    Filter by Difficulty
                  </h4>
                  {difficulties.map((difficulty) => (
                    <div
                      key={difficulty}
                      className="flex items-center space-x-2"
                    >
                      <Checkbox
                        checked={filters.difficulties.includes(difficulty)}
                        onCheckedChange={() =>
                          toggleArrayFilter("difficulties", difficulty)
                        }
                        data-testid={`checkbox-difficulty-${difficulty.toLowerCase()}`}
                      />
                      <label className="text-sm font-medium cursor-pointer">
                        {difficulty}
                      </label>
                    </div>
                  ))}
                </div>
              </PopoverContent>
            </Popover>

            {/* Companies Filter */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className="h-10 border-gray-200 hover:border-orange-500"
                  data-testid="button-companies-filter"
                >
                  <Building2 className="w-4 h-4 mr-2" />
                  Companies
                  {filters.companies.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="ml-2 bg-orange-100 text-orange-700"
                    >
                      {filters.companies.length}
                    </Badge>
                  )}
                  <ChevronDown className="w-4 h-4 ml-2" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80" align="start">
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900">
                    Filter by Companies
                  </h4>
                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {allCompanies.map((company: string) => (
                      <div
                        key={company}
                        className="flex items-center space-x-2"
                      >
                        <Checkbox
                          checked={filters.companies.includes(company)}
                          onCheckedChange={() =>
                            toggleArrayFilter("companies", company)
                          }
                          data-testid={`checkbox-company-${company
                            .toLowerCase()
                            .replace(/\s+/g, "-")}`}
                        />
                        <label className="text-sm font-medium cursor-pointer">
                          {company}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              </PopoverContent>
            </Popover>

            {/* Status Filter - Only show if user is authenticated */}
            {user && (
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="h-10 border-gray-200 hover:border-orange-500"
                    data-testid="button-status-filter"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Status
                    {filters.status !== "all" && (
                      <Badge
                        variant="secondary"
                        className="ml-2 bg-orange-100 text-orange-700"
                      >
                        1
                      </Badge>
                    )}
                    <ChevronDown className="w-4 h-4 ml-2" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64" align="start">
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">
                      Filter by Status
                    </h4>
                    {[
                      { value: "all", label: "All Problems" },
                      { value: "solved", label: "Solved" },
                      { value: "unsolved", label: "Unsolved" },
                    ].map((option) => (
                      <div
                        key={option.value}
                        className="flex items-center space-x-2"
                      >
                        <Checkbox
                          checked={filters.status === option.value}
                          onCheckedChange={() =>
                            updateFilter("status", option.value)
                          }
                          data-testid={`checkbox-status-${option.value}`}
                        />
                        <label className="text-sm font-medium cursor-pointer">
                          {option.label}
                        </label>
                      </div>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            )}

            {/* Clear Filters */}
            {getActiveFilterCount() > 0 && (
              <Button
                variant="ghost"
                onClick={clearFilters}
                className="h-10 text-gray-600 hover:text-gray-900"
                data-testid="button-clear-filters"
              >
                <X className="w-4 h-4 mr-2" />
                Clear filters
              </Button>
            )}
          </div>

          {/* Active Filter Chips */}
          <AnimatePresence>
            {getActiveFilterCount() > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap gap-2"
              >
                {filters.difficulties.map((difficulty) => (
                  <motion.div
                    key={`difficulty-${difficulty}`}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <Badge
                      variant="secondary"
                      className="bg-orange-100 text-orange-700 hover:bg-orange-200 cursor-pointer"
                      onClick={() =>
                        toggleArrayFilter("difficulties", difficulty)
                      }
                      data-testid={`chip-difficulty-${difficulty.toLowerCase()}`}
                    >
                      {difficulty}
                      <X className="w-3 h-3 ml-1" />
                    </Badge>
                  </motion.div>
                ))}
                {filters.companies.map((company) => (
                  <motion.div
                    key={`company-${company}`}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <Badge
                      variant="secondary"
                      className="bg-blue-100 text-blue-700 hover:bg-blue-200 cursor-pointer"
                      onClick={() => toggleArrayFilter("companies", company)}
                      data-testid={`chip-company-${company
                        .toLowerCase()
                        .replace(/\s+/g, "-")}`}
                    >
                      {company}
                      <X className="w-3 h-3 ml-1" />
                    </Badge>
                  </motion.div>
                ))}
                {filters.tags.map((tag) => (
                  <motion.div
                    key={`tag-${tag}`}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <Badge
                      variant="secondary"
                      className="bg-purple-100 text-purple-700 hover:bg-purple-200 cursor-pointer"
                      onClick={() => toggleArrayFilter("tags", tag)}
                      data-testid={`chip-tag-${tag
                        .toLowerCase()
                        .replace(/\s+/g, "-")}`}
                    >
                      {tag}
                      <X className="w-3 h-3 ml-1" />
                    </Badge>
                  </motion.div>
                ))}
                {filters.status !== "all" && (
                  <motion.div
                    key={`status-${filters.status}`}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <Badge
                      variant="secondary"
                      className="bg-green-100 text-green-700 hover:bg-green-200 cursor-pointer"
                      onClick={() => updateFilter("status", "all")}
                      data-testid={`chip-status-${filters.status}`}
                    >
                      {filters.status === "solved" ? "Solved" : "Unsolved"}
                      <X className="w-3 h-3 ml-1" />
                    </Badge>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Main Content Area - Table and Tags Side by Side */}
        <div className="flex gap-8">
          {/* Left Side - Table and Results */}
          <div className="flex-1">
            {/* Results Summary */}
            <div className="mb-6">
              <p className="text-gray-600">
                Showing{" "}
                <span className="font-semibold text-gray-900">
                  {filteredProblems.length}
                </span>{" "}
                of{" "}
                <span className="font-semibold text-gray-900">
                  {problems?.length || 0}
                </span>{" "}
                problems
              </p>
            </div>

            {/* Problems Table */}
            {isLoading ? (
              <div className="space-y-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="h-16 bg-gray-200 rounded" />
                  </div>
                ))}
              </div>
            ) : filteredProblems.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-16"
              >
                <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Search className="w-12 h-12 text-gray-400" />
                </div>
                <h3 className="text-2xl font-semibold text-gray-900 mb-2">
                  No problems found
                </h3>
                <p className="text-gray-600 mb-6">
                  Try changing your filters or search terms
                </p>
                <Button
                  onClick={clearFilters}
                  variant="outline"
                  data-testid="button-clear-all-filters"
                >
                  Clear all filters
                </Button>
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="border rounded-lg overflow-hidden bg-white"
              >
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="font-semibold text-gray-900">
                        Company
                      </TableHead>
                      <TableHead className="font-semibold text-gray-900">
                        Title
                      </TableHead>
                      <TableHead className="font-semibold text-gray-900">
                        Description
                      </TableHead>
                      <TableHead className="font-semibold text-gray-900">
                        Difficulty
                      </TableHead>
                      <TableHead className="font-semibold text-gray-900">
                        Status
                      </TableHead>
                      <TableHead className="font-semibold text-gray-900">
                        Submissions
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredProblems.map((problem, index) => (
                      <motion.tr
                        key={problem.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.02 }}
                        className="hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() =>
                          (window.location.href = `/problems/${problem.id}`)
                        }
                        data-testid={`row-problem-${problem.id}`}
                      >
                        <TableCell className="py-4 w-32">
                          <div className="flex flex-wrap gap-1">
                            <CompanyLogo
                              companyName={problem.company}
                              variant="badge"
                              size="sm"
                              showFallback={true}
                              data-testid={`company-badge-${problem.id}`}
                            />
                          </div>
                        </TableCell>

                        <TableCell className="py-4 max-w-xs">
                          <h3 className="font-medium text-gray-900 hover:text-orange-600 transition-colors truncate">
                            {problem.title}
                          </h3>
                        </TableCell>

                        <TableCell className="py-4 max-w-md">
                          <div className="text-gray-600 text-sm line-clamp-2">
                            <ReactMarkdown 
                              remarkPlugins={[remarkGfm]}
                              components={{
                                // Flatten all elements for preview - keep formatting but avoid line breaks
                                p: ({children}) => <span className="inline">{children} </span>,
                                strong: ({children}) => <strong className="font-semibold text-gray-800">{children}</strong>,
                                em: ({children}) => <em className="italic">{children}</em>,
                                code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                                h1: ({children}) => <span className="font-bold text-gray-800">{children} </span>,
                                h2: ({children}) => <span className="font-semibold text-gray-800">{children} </span>,
                                h3: ({children}) => <span className="font-medium text-gray-800">{children} </span>,
                                ul: ({children}) => <span>{children}</span>,
                                ol: ({children}) => <span>{children}</span>,
                                li: ({children}) => <span>{children} • </span>,
                                blockquote: ({children}) => <span className="italic text-blue-600">"{children}" </span>,
                                // Tables and code blocks are hidden in preview
                                table: () => <span className="text-blue-600 font-medium">[Table] </span>,
                                pre: () => <span className="text-green-600 font-medium">[Code] </span>,
                              }}
                            >
                              {(() => {
                                // Get first paragraph or first 150 chars to avoid breaking markdown syntax
                                const desc = problem.question.description;
                                const firstParagraph = desc.split('\n\n')[0];
                                if (firstParagraph.length > 150) {
                                  return firstParagraph.substring(0, 150) + '...';
                                }
                                return firstParagraph + (desc.length > firstParagraph.length ? '...' : '');
                              })()}
                            </ReactMarkdown>
                          </div>
                        </TableCell>

                        <TableCell className="py-4">
                          <DifficultyBadge
                            difficulty={problem.difficulty}
                            variant="badge"
                            size="sm"
                            showIcon={true}
                            data-testid={`difficulty-badge-${problem.id}`}
                          />
                        </TableCell>

                        <TableCell className="py-4">
                          <div className="flex items-center justify-center">
                            {problem.isUserSolved ? (
                              <div
                                className="text-green-600"
                                data-testid={`dumbbell-solved-${problem.id}`}
                              >
                                <Dumbbell className="w-5 h-5" />
                              </div>
                            ) : null}
                          </div>
                        </TableCell>

                        <TableCell className="py-4">
                          <div className="flex items-center space-x-1 text-sm text-gray-500">
                            <Users className="w-4 h-4" />
                            <span>{problem.solvedCount}</span>
                          </div>
                        </TableCell>
                      </motion.tr>
                    ))}
                  </TableBody>
                </Table>
              </motion.div>
            )}

            {/* Stats Footer */}
            {!isLoading && filteredProblems.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="mt-16 bg-gray-50 rounded-2xl p-8"
              >
                <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                  <div>
                    <div className="text-3xl font-bold text-gray-900">
                      {filteredProblems.length}
                    </div>
                    <div className="text-sm text-gray-600">Total Problems</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-green-600">
                      {
                        filteredProblems.filter((p) => p.difficulty === "Easy")
                          .length
                      }
                    </div>
                    <div className="text-sm text-gray-600">Easy</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-orange-600">
                      {
                        filteredProblems.filter(
                          (p) => p.difficulty === "Medium"
                        ).length
                      }
                    </div>
                    <div className="text-sm text-gray-600">Medium</div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-red-600">
                      {
                        filteredProblems.filter((p) => p.difficulty === "Hard")
                          .length
                      }
                    </div>
                    <div className="text-sm text-gray-600">Hard</div>
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Right Sidebar - Tags */}
          <div className="w-80">
            {allTags.length > 0 && (
              <div className="sticky top-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">
                  Tags
                </h3>
                <div className="flex flex-wrap gap-1.5 max-h-96 overflow-y-auto">
                  {allTags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => toggleArrayFilter("tags", tag)}
                      className={`
                    px-3 py-1.5 rounded-full text-sm font-medium transition-colors duration-200
                    ${
                      filters.tags.includes(tag)
                        ? "bg-orange-500 text-white border border-orange-500"
                        : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100 hover:border-gray-400"
                    }
                  `}
                    >
                      {tag} ({getTagCount(tag)})
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
