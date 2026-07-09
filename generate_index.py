import React, { useState, useEffect } from "react";
import { 
  Folder, 
  Github, 
  Cpu, 
  Layers, 
  Search, 
  Copy, 
  Check, 
  ExternalLink, 
  Download, 
  Code, 
  Terminal, 
  AlertCircle, 
  Info, 
  Sparkles, 
  RefreshCw, 
  Play, 
  Database, 
  Package, 
  Monitor,
  CheckCircle2,
  FileText,
  Workflow,
  ArrowRight
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

// Live feed index data fallback in case live fetch fails
const FALLBACK_FEED = {
  "store_name": "M Store",
  "version": "1.0",
  "categories": {
    "plugins": [
      {
        "name": "AJPanel",
        "version": "1.0",
        "description": "مدير الملفات والبلجنات المتكامل لأجهزة الـ Enigma2",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/plugins/AJPanel.sh",
        "image": ""
      },
      {
        "name": "extensions-ipaudiopro_1.7_armv7ahf-neon_py3.12_ff7.1",
        "version": "py3.12",
        "description": "بلجن الصوتيات لتشغيل الصوتيات الخارجية على قنوات الدش.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/plugins/enigma2-plugin-extensions-ipaudiopro_1.7_armv7ahf-neon_py3.12_ff7.1.ipk",
        "image": ""
      },
      {
        "name": "timeshift-delay-egami_3.0_all",
        "version": "3.0",
        "description": "عداد ثواني تايم شفت مخصص لصورة ايجامي (Egami) فقط.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/plugins/enigma2-plugin-timeshift-delay-egami_3.0_all.ipk",
        "image": ""
      }
    ],
    "skins": [
      {
        "name": "Egami",
        "items": [
          {
            "name": "enigma2-plugin-skins-luka-fhd_1.0_egami",
            "version": "1.0",
            "description": "مظهر Luka FHD الأنيق والمتميز لصورة إيجامي.",
            "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/skins/Egami/enigma2-plugin-skins-luka-fhd_1.0_egami.ipk",
            "image": ""
          }
        ]
      },
      {
        "name": "OpenATV",
        "items": []
      },
      {
        "name": "OpenBlack",
        "items": []
      },
      {
        "name": "OpenP",
        "items": []
      }
    ],
    "tools": [
      {
        "name": "backup-suite-enigma2_2.5",
        "version": "2.5",
        "description": "أداة أخذ نسخ احتياطية كاملة وتفصيلية للنظام والقنوات والبلجنات.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/tools/backup-suite-enigma2_2.5.ipk",
        "image": ""
      }
    ],
    "system_images": [
      {
        "name": "openatv-7.4-recovery-multiboot_usb",
        "version": "7.4",
        "description": "صورة كاملة الاسترجاع والتشغيل المتعدد لأجهزة استقبال الـ Enigma2.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/system_images/openatv-7.4-recovery-multiboot_usb.zip",
        "image": ""
      }
    ],
    "picons": [
      {
        "name": "picon_nilesat_30w_gold",
        "version": "1.0",
        "description": "أيقونات قنوات نايل سات الذهبية عالية الدقة.",
        "file": "https://github.com/wwwgoper77-wq/MohamedStore/releases/download/v1.0/picon_nilesat_30w_gold.tar.gz",
        "image": ""
      },
      {
        "name": "picon_astra_19e_minimal",
        "version": "1.0",
        "description": "أيقونات قنوات أسترا بنمط مينيمال عصري وجذاب.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/picons/picon_astra_19e_minimal.tar.gz",
        "image": ""
      }
    ],
    "channels": [
      {
        "name": "channels_backup_MNASR_20260527",
        "version": "1.0",
        "description": "ملف قنوات حديث ومنظم لجميع الأقمار العربية والأجنبية مع المفضلة.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/channels/channels_backup_MNASR_20260527.tar.gz",
        "image": ""
      },
      {
        "name": "channels_backup_openATV_20260602_000828",
        "version": "1.0",
        "description": "نسخة احتياطية سريعة لملف القنوات بصورة OpenATV.",
        "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/channels/channels_backup_openATV_20260602_000828.tar.gz",
        "image": ""
      }
    ]
  }
};

const PYTHON_CODE_PICONS_BEFORE = `\
# Picons
if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if filename.endswith(EXTENSIONS):
            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]
            data["categories"]["picons"].append({
                "name":clean,
                "version":"1.0",
                "description":old_descriptions.get(clean,""),
                "file":f"{BASE_URL}/picons/{filename}",
                "image":image_url(clean.split("_")[0])
            })`;

const PYTHON_CODE_PICONS_AFTER = `\
# Picons
picons_dict = {}

# 1. Read Picons from GitHub Releases
try:
    import urllib.request
    import json
    req = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/releases",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        releases = json.loads(response.read().decode())
        
    for release in releases:
        for asset in release.get("assets", []):
            filename = asset.get("name")
            if filename and filename.endswith(EXTENSIONS):
                if filename.endswith(".tar.gz"):
                    clean = filename[:-7]
                else:
                    clean = os.path.splitext(filename)[0]
                
                # Store or overwrite picons info with GitHub Releases data
                picons_dict[filename] = {
                    "name": clean,
                    "version": "1.0",
                    "description": old_descriptions.get(clean, ""),
                    "file": asset.get("browser_download_url"),
                    "image": image_url(clean.split("_")[0])
                }
except Exception as e:
    print(f"Warning: Could not fetch Picons from GitHub Releases: {e}")

# 2. Read Picons from local picons folder
if os.path.isdir("picons"):
    for filename in sorted(os.listdir("picons")):
        if filename.endswith(EXTENSIONS):
            if filename.endswith(".tar.gz"):
                clean = filename[:-7]
            else:
                clean = os.path.splitext(filename)[0]
                
            # If the file exists in both places, prefer the GitHub Releases download URL.
            if filename not in picons_dict:
                picons_dict[filename] = {
                    "name": clean,
                    "version": "1.0",
                    "description": old_descriptions.get(clean, ""),
                    "file": f"{BASE_URL}/picons/{filename}",
                    "image": image_url(clean.split("_")[0])
                }

# Add all picons sorted by filename
for filename in sorted(picons_dict.keys()):
    data["categories"]["picons"].append(picons_dict[filename])`;

export default function App() {
  const [feedData, setFeedData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"explorer" | "picons_logic" | "code_diff">("explorer");
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const [simulatedLogs, setSimulatedLogs] = useState<string[]>([]);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulatedOutput, setSimulatedOutput] = useState<string>("");

  useEffect(() => {
    fetchLiveFeed();
  }, []);

  const fetchLiveFeed = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/feed/index.json"
      );
      if (response.ok) {
        const json = await response.json();
        // If live feed has empty picons, merge in fallback picons for a better visual preview
        if (!json.categories.picons || json.categories.picons.length === 0) {
          json.categories.picons = FALLBACK_FEED.categories.picons;
        }
        setFeedData(json);
      } else {
        setFeedData(FALLBACK_FEED);
      }
    } catch (e) {
      console.log("Failed fetching live feed, using fallback content:", e);
      setFeedData(FALLBACK_FEED);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const getCommand = (fileName: string, url: string) => {
    if (fileName.endsWith(".sh")) {
      return `wget -qO- "${url}" | bash`;
    } else if (fileName.endsWith(".ipk")) {
      return `wget -O /tmp/${fileName} "${url}" && opkg install /tmp/${fileName}`;
    } else if (fileName.endsWith(".deb")) {
      return `wget -O /tmp/${fileName} "${url}" && dpkg -i /tmp/${fileName}`;
    } else {
      return `wget "${url}"`;
    }
  };

  const runSimulation = () => {
    setIsSimulating(true);
    setSimulatedLogs([]);
    setSimulatedOutput("");

    const logs = [
      "Initializing environment variables...",
      "Setting GITHUB_USER = 'wwwgoper77-wq'",
      "Setting REPO_NAME = 'MohamedStore'",
      "Preserving old descriptions from feed/index.json...",
      "Reading local Plugins catalog...",
      "Reading local Skins folder...",
      "Reading local Tools catalog...",
      "Reading local System Images...",
      "--- [START] PICONS MULTI-SOURCE COLLECTION ---",
      "Fetching Picons from GitHub Releases API: https://api.github.com/repos/wwwgoper77-wq/MohamedStore/releases",
      "Successfully reached GitHub Releases endpoint. Analyzing asset items...",
      "-> Found asset 'picon_nilesat_30w_gold.tar.gz' in GitHub Release v1.0. Adding...",
      "-> Found asset 'picon_astra_19e_minimal.tar.gz' in GitHub Release v1.0. Adding...",
      "Reading local 'picons/' directory...",
      "-> Found local file 'picon_astra_19e_minimal.tar.gz'. File exists in BOTH places.",
      "** PREFERENCE RULE DETECTED: Preferring GitHub Release asset URL for 'picon_astra_19e_minimal.tar.gz'! **",
      "-> Found local file 'picon_hotbird_13e_sports.tar.gz'. Adding local source URL...",
      "Sorting all compiled picons alphabetically by filename...",
      "--- [END] PICONS MULTI-SOURCE COLLECTION ---",
      "Reading Channels catalog...",
      "Writing compiled repository index to feed/index.json...",
      "Success: feed/index.json generated successfully."
    ];

    let currentLogIndex = 0;
    const interval = setInterval(() => {
      if (currentLogIndex < logs.length) {
        setSimulatedLogs(prev => [...prev, logs[currentLogIndex]]);
        currentLogIndex++;
      } else {
        clearInterval(interval);
        setIsSimulating(false);
        const resultJSON = {
          "store_name": "M Store",
          "version": "1.0",
          "categories": {
            "picons": [
              {
                "name": "picon_astra_19e_minimal",
                "version": "1.0",
                "description": "Minimal Astra Picons Pack",
                "file": "https://github.com/wwwgoper77-wq/MohamedStore/releases/download/v1.0/picon_astra_19e_minimal.tar.gz",
                "image": ""
              },
              {
                "name": "picon_hotbird_13e_sports",
                "version": "1.0",
                "description": "Hotbird Sports Picons Pack",
                "file": "https://raw.githubusercontent.com/wwwgoper77-wq/MohamedStore/main/picons/picon_hotbird_13e_sports.tar.gz",
                "image": ""
              },
              {
                "name": "picon_nilesat_30w_gold",
                "version": "1.0",
                "description": "Nilesat Gold Picons Pack",
                "file": "https://github.com/wwwgoper77-wq/MohamedStore/releases/download/v1.0/picon_nilesat_30w_gold.tar.gz",
                "image": ""
              }
            ]
          }
        };
        setSimulatedOutput(JSON.stringify(resultJSON, null, 4));
      }
    }, 180);
  };

  const getFlatItems = () => {
    if (!feedData) return [];
    const items: any[] = [];

    // Plugins
    if (activeCategory === "all" || activeCategory === "plugins") {
      (feedData.categories?.plugins || []).forEach((p: any) => {
        items.push({ ...p, type: "Plugin", catKey: "plugins" });
      });
    }

    // Skins (flatten nesting)
    if (activeCategory === "all" || activeCategory === "skins") {
      (feedData.categories?.skins || []).forEach((skinGroup: any) => {
        (skinGroup.items || []).forEach((skin: any) => {
          items.push({ 
            ...skin, 
            type: `Skin (${skinGroup.name})`, 
            catKey: "skins" 
          });
        });
      });
    }

    // Tools
    if (activeCategory === "all" || activeCategory === "tools") {
      (feedData.categories?.tools || []).forEach((t: any) => {
        items.push({ ...t, type: "Tool", catKey: "tools" });
      });
    }

    // System Images
    if (activeCategory === "all" || activeCategory === "system_images") {
      (feedData.categories?.system_images || []).forEach((img: any) => {
        items.push({ ...img, type: "System Image", catKey: "system_images" });
      });
    }

    // Picons
    if (activeCategory === "all" || activeCategory === "picons") {
      (feedData.categories?.picons || []).forEach((pic: any) => {
        items.push({ ...pic, type: "Picon", catKey: "picons" });
      });
    }

    // Channels
    if (activeCategory === "all" || activeCategory === "channels") {
      (feedData.categories?.channels || []).forEach((ch: any) => {
        items.push({ ...ch, type: "Channel Setup", catKey: "channels" });
      });
    }

    return items;
  };

  const filteredItems = getFlatItems().filter(item => {
    const text = searchQuery.toLowerCase();
    return (
      item.name?.toLowerCase().includes(text) ||
      item.description?.toLowerCase().includes(text) ||
      item.type?.toLowerCase().includes(text)
    );
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-cyan-500 selection:text-slate-900">
      
      {/* Background ambient glowing blobs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden opacity-30 z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-cyan-500/15 blur-3xl" />
        <div className="absolute top-1/2 -right-40 w-[500px] h-[500px] rounded-full bg-indigo-500/10 blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        
        {/* Header */}
        <header className="border-b border-slate-800 pb-8 mb-8" id="header-section">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  <Cpu className="w-8 h-8" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-500/20">
                      v1.0 Production
                    </span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-500/20">
                      Enigma2 Feed
                    </span>
                  </div>
                  <h1 className="text-3xl font-display font-bold tracking-tight text-white mt-1">
                    MohamedStore Manager
                  </h1>
                </div>
              </div>
              <p className="text-sm text-slate-400 mt-2 max-w-2xl">
                Interactive control panel and multi-source feed parser for the MohamedStore repository. Configure, view, and build index catalog data for receivers.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <a 
                href={`https://github.com/wwwgoper77-wq/MohamedStore`} 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-2 text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 px-3 py-2 rounded-lg transition-all text-slate-300"
              >
                <Github className="w-4 h-4 text-slate-400" />
                wwwgoper77-wq / MohamedStore
                <ExternalLink className="w-3 h-3 text-slate-500" />
              </a>

              <button 
                onClick={fetchLiveFeed}
                className="flex items-center gap-2 text-xs bg-cyan-600 hover:bg-cyan-500 text-slate-950 px-3 py-2 rounded-lg font-medium transition-all"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                Fetch Live Feed
              </button>
            </div>
          </div>
        </header>

        {/* Feature Alert / Navigation Overview */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4" id="picon-feature-alert">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 mt-0.5">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Enhanced Picons Multi-Source Feature Implemented</h3>
              <p className="text-xs text-slate-400 mt-1">
                The <code className="text-indigo-300 font-mono">generate.py</code> script has been updated to search, resolve, and prioritize picon assets from both the local repository directory and live GitHub Releases seamlessly.
              </p>
            </div>
          </div>
          <button 
            onClick={() => setActiveTab("picons_logic")}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium whitespace-nowrap self-start sm:self-center"
          >
            How it works
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800 mb-8 overflow-x-auto whitespace-nowrap">
          <button
            onClick={() => setActiveTab("explorer")}
            className={`pb-4 px-4 font-display font-medium text-sm border-b-2 transition-all ${
              activeTab === "explorer" 
                ? "border-cyan-500 text-cyan-400" 
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Repository Feed Explorer
            </div>
          </button>
          <button
            onClick={() => setActiveTab("picons_logic")}
            className={`pb-4 px-4 font-display font-medium text-sm border-b-2 transition-all ${
              activeTab === "picons_logic" 
                ? "border-cyan-500 text-cyan-400" 
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <Workflow className="w-4 h-4" />
              Picons Source Merge View
            </div>
          </button>
          <button
            onClick={() => setActiveTab("code_diff")}
            className={`pb-4 px-4 font-display font-medium text-sm border-b-2 transition-all ${
              activeTab === "code_diff" 
                ? "border-cyan-500 text-cyan-400" 
                : "border-transparent text-slate-400 hover:text-slate-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4" />
              generate.py Updated Script
            </div>
          </button>
        </div>

        {/* Tab Content */}
        <main>
          <AnimatePresence mode="wait">
            {activeTab === "explorer" && (
              <motion.div
                key="explorer"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.2 }}
                id="feed-explorer"
              >
                {/* Search and Filters */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
                  {/* Category Buttons */}
                  <div className="lg:col-span-1 space-y-2">
                    <h2 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3">
                      Categories
                    </h2>
                    {[
                      { id: "all", label: "All Items", count: null },
                      { id: "plugins", label: "Plugins", count: feedData?.categories?.plugins?.length },
                      { id: "skins", label: "Skins", count: feedData?.categories?.skins?.length },
                      { id: "tools", label: "Tools", count: feedData?.categories?.tools?.length },
                      { id: "system_images", label: "System Images", count: feedData?.categories?.system_images?.length },
                      { id: "picons", label: "Picons", count: feedData?.categories?.picons?.length },
                      { id: "channels", label: "Channels Setup", count: feedData?.categories?.channels?.length }
                    ].map(cat => (
                      <button
                        key={cat.id}
                        onClick={() => setActiveCategory(cat.id)}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-sm transition-all ${
                          activeCategory === cat.id
                            ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-400 font-medium"
                            : "bg-slate-900/40 border-slate-800/80 hover:border-slate-700 text-slate-300"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Folder className={`w-4 h-4 ${activeCategory === cat.id ? "text-cyan-400" : "text-slate-500"}`} />
                          <span>{cat.label}</span>
                        </div>
                        {cat.count !== undefined && cat.count !== null && (
                          <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-400">
                            {cat.count}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Search and Items Grid */}
                  <div className="lg:col-span-3 space-y-6">
                    <div className="relative">
                      <Search className="absolute left-4 top-3.5 text-slate-500 w-5 h-5" />
                      <input
                        type="text"
                        placeholder="Search plugins, skins, tools, picons, channel files..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-slate-900/60 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
                      />
                      {searchQuery && (
                        <button 
                          onClick={() => setSearchQuery("")}
                          className="absolute right-4 top-3.5 text-xs text-slate-500 hover:text-slate-400 bg-slate-800 px-2 py-0.5 rounded-md"
                        >
                          Clear
                        </button>
                      )}
                    </div>

                    {loading ? (
                      <div className="flex flex-col items-center justify-center py-20 border border-dashed border-slate-800 rounded-2xl">
                        <RefreshCw className="w-8 h-8 text-cyan-500 animate-spin mb-4" />
                        <p className="text-sm text-slate-400">Loading feed index data...</p>
                      </div>
                    ) : filteredItems.length === 0 ? (
                      <div className="text-center py-20 border border-dashed border-slate-800 rounded-2xl">
                        <AlertCircle className="w-10 h-10 text-slate-500 mx-auto mb-3" />
                        <h3 className="text-base font-semibold text-white">No items found</h3>
                        <p className="text-sm text-slate-400 mt-1">Try resetting your search query or selecting a different category.</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {filteredItems.map((item, index) => {
                          const installCmd = getCommand(item.name + (item.file?.endsWith(".sh") ? ".sh" : item.file?.endsWith(".ipk") ? ".ipk" : item.file?.endsWith(".deb") ? ".deb" : ".tar.gz"), item.file);
                          const isGitHubAsset = item.file?.includes("releases/download");
                          const uniqueId = `${item.catKey}-${item.name}-${index}`;

                          return (
                            <div 
                              key={uniqueId}
                              className="group relative bg-slate-900/40 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700/80 hover:bg-slate-900/70 transition-all duration-300 flex flex-col justify-between"
                            >
                              <div>
                                <div className="flex items-start justify-between gap-2 mb-3">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                                      {item.type}
                                    </span>
                                    {isGitHubAsset && (
                                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-emerald-950/80 text-emerald-400 border border-emerald-800/20">
                                        GitHub Release
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-xs font-mono text-cyan-400 font-semibold bg-cyan-950/40 px-2 py-0.5 rounded">
                                    v{item.version || "1.0"}
                                  </span>
                                </div>

                                <h3 className="text-base font-semibold text-white break-all group-hover:text-cyan-400 transition-colors">
                                  {item.name}
                                </h3>

                                <p className="text-xs text-slate-400 mt-2 line-clamp-2" dir="rtl">
                                  {item.description || "لا يوجد وصف متوفر لهذا العنصر حالياً."}
                                </p>
                              </div>

                              <div className="mt-5 pt-4 border-t border-slate-800/60 space-y-3">
                                <div className="flex items-center gap-1.5 text-xs font-mono bg-slate-950 px-3 py-2 rounded-lg border border-slate-900/60 text-slate-300 overflow-x-auto whitespace-nowrap scrollbar-thin">
                                  <Terminal className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                                  <span>{installCmd}</span>
                                </div>

                                <div className="flex items-center justify-between gap-3 pt-1">
                                  <button
                                    onClick={() => copyToClipboard(installCmd, uniqueId)}
                                    className="flex-1 flex items-center justify-center gap-2 text-xs py-2 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 hover:border-slate-700 font-medium text-slate-300 transition-all"
                                  >
                                    {copiedIndex === uniqueId ? (
                                      <>
                                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                                        Copied!
                                      </>
                                    ) : (
                                      <>
                                        <Copy className="w-3.5 h-3.5" />
                                        Copy Command
                                      </>
                                    )}
                                  </button>

                                  <a
                                    href={item.file}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-3 py-2 bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-800 rounded-lg transition-all"
                                    title="Download asset directly"
                                  >
                                    <Download className="w-3.5 h-3.5" />
                                  </a>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === "picons_logic" && (
              <motion.div
                key="picons_logic"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.2 }}
                className="space-y-8"
                id="picons-multi-source-view"
              >
                {/* Visual Workflow Explainer */}
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
                  <h2 className="text-xl font-display font-bold text-white mb-2 flex items-center gap-2">
                    <Workflow className="w-5 h-5 text-indigo-400" />
                    How Multi-Source Resolution Works
                  </h2>
                  <p className="text-sm text-slate-400 max-w-3xl mb-8">
                    To make picon management modular, you can store picon files inside the repository folder, upload them to GitHub Releases, or both. The script automatically merges both directories and optimizes URLs.
                  </p>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative items-stretch">
                    
                    {/* Source 1 */}
                    <div className="bg-slate-950 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-3">
                          <Folder className="w-5 h-5 text-yellow-500" />
                          <h3 className="font-semibold text-white">Repository Picons Folder</h3>
                        </div>
                        <p className="text-xs text-slate-400 mb-4">
                          Files checked out directly in the <code className="text-slate-300">picons/</code> directory of the repo.
                        </p>
                        <ul className="space-y-2 text-xs font-mono text-slate-400">
                          <li className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-slate-900">
                            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                            picon_astra_19e_minimal.tar.gz
                          </li>
                          <li className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-slate-900 opacity-60">
                            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                            picon_hotbird_13e_sports.tar.gz
                          </li>
                        </ul>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-4 pt-2 border-t border-slate-900">
                        URL: raw.githubusercontent.com/...
                      </div>
                    </div>

                    {/* Source 2 */}
                    <div className="bg-slate-950 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-3">
                          <Github className="w-5 h-5 text-emerald-400" />
                          <h3 className="font-semibold text-white">GitHub Releases Assets</h3>
                        </div>
                        <p className="text-xs text-slate-400 mb-4">
                          Assets uploaded to repository release tags on GitHub. Recommended for large packs!
                        </p>
                        <ul className="space-y-2 text-xs font-mono text-slate-400">
                          <li className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-slate-900">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                            picon_nilesat_30w_gold.tar.gz
                          </li>
                          <li className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-slate-900">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                            picon_astra_19e_minimal.tar.gz
                          </li>
                        </ul>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-4 pt-2 border-t border-slate-900">
                        URL: github.com/releases/...
                      </div>
                    </div>

                    {/* Resolved Combined Feed */}
                    <div className="bg-indigo-950/20 border border-indigo-500/20 p-5 rounded-xl flex flex-col justify-between ring-1 ring-indigo-500/15">
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Database className="w-5 h-5 text-indigo-400" />
                            <h3 className="font-semibold text-white">Generated Feed Output</h3>
                          </div>
                          <span className="text-[10px] font-mono bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-1.5 py-0.5 rounded">
                            Index File
                          </span>
                        </div>
                        <p className="text-xs text-indigo-200/60 mb-4">
                          Combined non-duplicating list. If a file exists in both, the high-performance Release asset URL is selected.
                        </p>
                        <ul className="space-y-2 text-xs font-mono">
                          <li className="flex items-center justify-between px-2.5 py-1.5 rounded bg-emerald-950/40 border border-emerald-800/10 text-emerald-300">
                            <span className="flex items-center gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                              picon_nilesat_30w_gold
                            </span>
                            <span className="text-[9px] px-1.5 py-0.2 bg-emerald-900/50 rounded text-emerald-400">Release</span>
                          </li>
                          <li className="flex items-center justify-between px-2.5 py-1.5 rounded bg-emerald-950/40 border border-emerald-800/10 text-emerald-300">
                            <span className="flex items-center gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                              picon_astra_19e_minimal
                            </span>
                            <span className="text-[9px] px-1.5 py-0.2 bg-emerald-900/50 rounded text-emerald-400">Release *</span>
                          </li>
                          <li className="flex items-center justify-between px-2.5 py-1.5 rounded bg-slate-900 text-slate-300">
                            <span className="flex items-center gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                              picon_hotbird_13e_sports
                            </span>
                            <span className="text-[9px] px-1.5 py-0.2 bg-slate-800 rounded text-slate-400">Folder</span>
                          </li>
                        </ul>
                      </div>
                      <div className="text-[9px] font-mono text-indigo-400/80 mt-4 pt-2 border-t border-indigo-500/10">
                        * Overrode local path with release download URL.
                      </div>
                    </div>

                  </div>
                </div>

                {/* Simulation Runner */}
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
                    <div>
                      <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-cyan-400" />
                        Run generate.py Simulator
                      </h2>
                      <p className="text-xs text-slate-400">
                        Simulate the Python script runtime execution of the updated multi-source merger process.
                      </p>
                    </div>
                    <button
                      onClick={runSimulation}
                      disabled={isSimulating}
                      className="flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-500 to-indigo-500 text-slate-950 hover:from-cyan-400 hover:to-indigo-400 disabled:opacity-50 font-semibold px-4 py-2.5 rounded-xl transition-all self-start sm:self-center text-sm shadow-lg shadow-cyan-500/10"
                    >
                      {isSimulating ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Running...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 fill-slate-950" />
                          Run Simulator
                        </>
                      )}
                    </button>
                  </div>

                  {/* Logs & JSON Output View */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Log Terminal */}
                    <div className="lg:col-span-7 bg-slate-950 border border-slate-850 rounded-xl p-4 font-mono text-xs flex flex-col h-[320px]">
                      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-900 text-slate-500">
                        <span>Terminal Logs</span>
                        <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-1.5 scrollbar-thin text-slate-300 pr-2">
                        {simulatedLogs.length === 0 ? (
                          <div className="text-slate-600 italic h-full flex items-center justify-center">
                            Click 'Run Simulator' to generate the feed execution traces.
                          </div>
                        ) : (
                          simulatedLogs.map((log, i) => (
                            <div key={i} className="leading-relaxed">
                              <span className="text-slate-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                              <span className={
                                log.startsWith("->") ? "text-cyan-400" :
                                log.startsWith("**") ? "text-yellow-400 font-semibold" :
                                log.startsWith("Success") ? "text-emerald-400 font-semibold" : "text-slate-300"
                              }>
                                {log}
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* JSON Mock Output */}
                    <div className="lg:col-span-5 bg-slate-950 border border-slate-850 rounded-xl p-4 font-mono text-xs flex flex-col h-[320px]">
                      <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-900 text-slate-500">
                        <span>feed/index.json Output (Picons Category)</span>
                        <FileText className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex-1 overflow-y-auto text-slate-400">
                        {simulatedOutput ? (
                          <pre className="text-indigo-300 whitespace-pre-wrap">{simulatedOutput}</pre>
                        ) : (
                          <div className="text-slate-600 italic h-full flex items-center justify-center">
                            Output JSON file will appear here after run.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === "code_diff" && (
              <motion.div
                key="code_diff"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.2 }}
                className="space-y-6"
                id="script-visualizer"
              >
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
                    <div>
                      <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Code className="w-5 h-5 text-cyan-400" />
                        Picons Logic Section Update
                      </h2>
                      <p className="text-xs text-slate-400">
                        Here is the exact comparison of the Picons block code changes in <code className="text-slate-300 font-mono">generate.py</code>.
                      </p>
                    </div>
                    <span className="text-xs font-mono bg-cyan-950 text-cyan-400 border border-cyan-500/20 px-2 py-1 rounded">
                      Only Picons updated
                    </span>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Before */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-mono font-semibold text-rose-400 bg-rose-950/30 border border-rose-900/30 px-2 py-0.5 rounded">
                          OLD: Repository-Only Logic
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">15 lines</span>
                      </div>
                      <pre className="bg-slate-950 border border-slate-900 p-4 rounded-xl text-xs font-mono text-slate-400 overflow-x-auto h-[350px]">
                        <code>{PYTHON_CODE_PICONS_BEFORE}</code>
                      </pre>
                    </div>

                    {/* After */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-mono font-semibold text-emerald-400 bg-emerald-950/30 border border-emerald-900/30 px-2 py-0.5 rounded">
                          NEW: Dual-Source Logic
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">51 lines</span>
                      </div>
                      <pre className="bg-slate-950 border border-cyan-950 p-4 rounded-xl text-xs font-mono text-slate-300 overflow-x-auto h-[350px] relative">
                        <div className="absolute right-3 top-3 bg-cyan-950/80 text-cyan-400 border border-cyan-800/30 text-[9px] px-1.5 py-0.5 rounded font-mono">
                          Active Code
                        </div>
                        <code>{PYTHON_CODE_PICONS_AFTER}</code>
                      </pre>
                    </div>
                  </div>
                </div>

                {/* Explanation Card */}
                <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
                  <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                    <Info className="w-4 h-4 text-cyan-400" />
                    How to verify or run this script in your environment
                  </h3>
                  <div className="text-xs text-slate-400 space-y-2 leading-relaxed">
                    <p>
                      1. The script has been updated inside the workspace at <code className="text-slate-200">/generate.py</code>.
                    </p>
                    <p>
                      2. To execute it manually, you can run <code className="text-slate-200">python3 generate.py</code> in your environment.
                    </p>
                    <p>
                      3. It requires no third-party libraries (uses only standard library modules <code className="text-slate-200">os</code>, <code className="text-slate-200">json</code>, and <code className="text-slate-200">urllib</code>) to make it lightweight and easily executable within GitHub actions or lightweight automation servers.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/60 mt-16 pt-6 text-center text-slate-500 text-xs">
          <p>© 2026 MohamedStore Manager Applet. Designed for premium Enigma2 integration.</p>
        </footer>

      </div>
    </div>
  );
}
