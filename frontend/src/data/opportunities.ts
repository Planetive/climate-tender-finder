export interface Opportunity {
  id: string;
  title: string;
  source: string;
  country: string;
  region: string;
  type: "Grant" | "RFP" | "Partnership" | "Tender";
  relevance: "High" | "Medium" | "Low";
  deadline: string;
  deadlineDate: Date;
  fundingAgency: string;
  tags: string[];
  summary: string;
  requiredAction: string;
  documents: { name: string; url: string }[];
  link: string; // Link to the original source/article
}

export const opportunities: Opportunity[] = [
  {
    id: "1",
    title: "Climate Resilience and Adaptation Grant for South Asia",
    source: "UNDP",
    country: "Pakistan",
    region: "South Asia",
    type: "Grant",
    relevance: "High",
    deadline: "Jan 15, 2025",
    deadlineDate: new Date("2025-01-15"),
    fundingAgency: "United Nations Development Programme",
    tags: ["Climate Finance", "Adaptation", "Resilience"],
    summary: "This grant supports climate adaptation initiatives in South Asian countries with a focus on building resilience in vulnerable communities. The program prioritizes projects that demonstrate measurable impact on reducing climate vulnerability and enhancing adaptive capacity at the local level.",
    requiredAction: "Submit EOI",
    documents: [
      { name: "Call for Proposals.pdf", url: "#" },
      { name: "Application Guidelines.pdf", url: "#" },
    ],
  },
  {
    id: "2",
    title: "Pakistan Renewable Energy Infrastructure RFP",
    source: "World Bank",
    country: "Pakistan",
    region: "South Asia",
    type: "RFP",
    relevance: "High",
    deadline: "Jan 20, 2025",
    deadlineDate: new Date("2025-01-20"),
    fundingAgency: "World Bank Group",
    tags: ["Energy Transition", "Infrastructure", "Renewable Energy"],
    summary: "Request for proposals for technical assistance in developing renewable energy infrastructure across Pakistan. The project aims to support the country's transition to clean energy by strengthening grid infrastructure and enabling solar and wind energy integration.",
    requiredAction: "Submit Proposal",
    documents: [
      { name: "RFP Document.pdf", url: "#" },
      { name: "Technical Requirements.pdf", url: "#" },
    ],
  },
  {
    id: "3",
    title: "MENA Climate Finance Partnership Call",
    source: "GCF",
    country: "MENA Region",
    region: "Middle East & North Africa",
    type: "Partnership",
    relevance: "High",
    deadline: "Feb 1, 2025",
    deadlineDate: new Date("2025-02-01"),
    fundingAgency: "Green Climate Fund",
    tags: ["Climate Finance", "MRV", "Partnership"],
    summary: "The Green Climate Fund is seeking accredited entities and partners for climate finance initiatives in the MENA region. This call focuses on developing robust MRV systems and climate finance tracking mechanisms for adaptation and mitigation projects.",
    requiredAction: "Partner Application",
    documents: [
      { name: "Partnership Framework.pdf", url: "#" },
    ],
  },
  {
    id: "4",
    title: "EU Horizon Climate Adaptation Innovation Call",
    source: "European Commission",
    country: "Global",
    region: "Global",
    type: "Grant",
    relevance: "Medium",
    deadline: "Feb 15, 2025",
    deadlineDate: new Date("2025-02-15"),
    fundingAgency: "European Commission - DG Research",
    tags: ["Innovation", "Adaptation", "Research"],
    summary: "Horizon Europe funding for innovative climate adaptation solutions. Open to international consortia with European partners. Focus areas include nature-based solutions, early warning systems, and climate-resilient urban planning.",
    requiredAction: "Submit Application",
    documents: [
      { name: "Work Programme.pdf", url: "#" },
      { name: "Proposal Template.docx", url: "#" },
    ],
  },
  {
    id: "5",
    title: "USAID Clean Energy Technical Assistance Tender",
    source: "USAID",
    country: "Pakistan",
    region: "South Asia",
    type: "Tender",
    relevance: "Medium",
    deadline: "Feb 28, 2025",
    deadlineDate: new Date("2025-02-28"),
    fundingAgency: "United States Agency for International Development",
    tags: ["Energy Transition", "Technical Assistance", "Capacity Building"],
    summary: "Technical assistance tender for clean energy sector support in Pakistan. The program aims to provide advisory services for policy development, regulatory framework enhancement, and private sector engagement in renewable energy.",
    requiredAction: "Submit Bid",
    documents: [
      { name: "Tender Notice.pdf", url: "#" },
      { name: "Scope of Work.pdf", url: "#" },
    ],
  },
  {
    id: "6",
    title: "ADB Climate Risk Assessment Study - South Asia",
    source: "ADB",
    country: "Regional",
    region: "South Asia",
    type: "RFP",
    relevance: "Medium",
    deadline: "Mar 10, 2025",
    deadlineDate: new Date("2025-03-10"),
    fundingAgency: "Asian Development Bank",
    tags: ["Climate Risk", "Assessment", "Research"],
    summary: "Consulting services for comprehensive climate risk assessment across South Asian developing member countries. The study will inform ADB's climate investment strategy and project pipeline development.",
    requiredAction: "Submit EOI",
    documents: [
      { name: "Terms of Reference.pdf", url: "#" },
    ],
  },
  {
    id: "7",
    title: "DFID Pakistan Climate Resilient Agriculture",
    source: "FCDO",
    country: "Pakistan",
    region: "South Asia",
    type: "Grant",
    relevance: "Low",
    deadline: "Mar 30, 2025",
    deadlineDate: new Date("2025-03-30"),
    fundingAgency: "UK Foreign, Commonwealth & Development Office",
    tags: ["Agriculture", "Adaptation", "Food Security"],
    summary: "Grant funding for climate-resilient agriculture programs in Pakistan. Focus on smallholder farmers, water management, and climate-smart agricultural practices.",
    requiredAction: "Submit Concept Note",
    documents: [
      { name: "Concept Note Template.docx", url: "#" },
    ],
  },
  {
    id: "8",
    title: "Islamic Development Bank Green Sukuk Initiative",
    source: "IsDB",
    country: "MENA Region",
    region: "Middle East & North Africa",
    type: "Partnership",
    relevance: "Low",
    deadline: "Apr 15, 2025",
    deadlineDate: new Date("2025-04-15"),
    fundingAgency: "Islamic Development Bank",
    tags: ["Green Finance", "Sukuk", "Islamic Finance"],
    summary: "Partnership call for green sukuk structuring and issuance support in MENA member countries. The initiative aims to mobilize Islamic finance for climate-positive investments.",
    requiredAction: "Expression of Interest",
    documents: [
      { name: "Initiative Overview.pdf", url: "#" },
    ],
  },
];
