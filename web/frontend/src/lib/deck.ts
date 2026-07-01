// GERADO por scratchpad/pptx_to_html.py a partir de AnonShield_TCC.pptx.
// Nao editar a mao: reexecutar o conversor. Traducoes EN sao mescladas por deck-en.ts.
export type Run = { pt: string; en: string; s: number; b: boolean; c: string | null; f: string };
export type Para = { a: string; runs: Run[] };
export type El = {
  kind: 'text' | 'shape' | 'img';
  x: number; y: number; w: number; h: number;
  anchor?: string; paras?: Para[];
  sub?: string; fill?: string | null; bw?: number; bc?: string | null; rx?: number;
  src?: string;
};
export type Slide = { n: number; els: El[] };
export const SLIDES: Slide[] = [
 {
  "n": 1,
  "els": [
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 11.333,
    "w": 86.252,
    "h": 0.4,
    "fill": "#110E09",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 14.667,
    "w": 87.002,
    "h": 21.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Anon",
        "en": "Anon",
        "s": 9.167,
        "b": true,
        "c": "#110E09",
        "f": "head"
       },
       {
        "pt": "Shield",
        "en": "Shield",
        "s": 9.167,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.9,
    "y": 39.333,
    "w": 84.002,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Pseudonimização segura e escalável de dados de incidentes e vulnerabilidades em CSIRTs",
        "en": "Pseudonimização segura e escalável de dados de incidentes e vulnerabilidades em CSIRTs",
        "s": 2.5,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 59.333,
    "w": 9.75,
    "h": 6.667,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "host:",
        "en": "host:",
        "s": 2.5,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 15.0,
    "y": 59.333,
    "w": 22.501,
    "h": 6.667,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "100.111.20.23",
        "en": "100.111.20.23",
        "s": 2.5,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 38.626,
    "y": 60.0,
    "w": 5.4,
    "h": 5.867,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 45.376,
    "y": 59.333,
    "w": 45.001,
    "h": 6.667,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "[IP_ADDRESS_a4f2b1c3]",
        "en": "[IP_ADDRESS_a4f2b1c3]",
        "s": 2.5,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 78.667,
    "w": 42.001,
    "h": 0.267,
    "fill": "#D0CABA",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 81.333,
    "w": 60.002,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Cristhian Kapelinski",
        "en": "Cristhian Kapelinski",
        "s": 2.5,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     },
     {
      "a": "left",
      "runs": [
       {
        "pt": "Orientador: Diego Kreutz",
        "en": "Orientador: Diego Kreutz",
        "s": 1.979,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     },
     {
      "a": "left",
      "runs": [
       {
        "pt": "Ciência da Computação, UNIPAMPA, Campus Alegrete",
        "en": "Ciência da Computação, UNIPAMPA, Campus Alegrete",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 59.251,
    "y": 84.0,
    "w": 33.376,
    "h": 12.534,
    "src": "/deck/slides/s01_0.webp"
   }
  ]
 },
 {
  "n": 2,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s02_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s02_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "O que é um CSIRT?",
        "en": "O que é um CSIRT?",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "02",
        "en": "02",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 23.333,
    "w": 30.751,
    "h": 16.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A equipe que cuida da segurança digital. ",
        "en": "A equipe que cuida da segurança digital. ",
        "s": 2.083,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       },
       {
        "pt": "Como os bombeiros, mas para ataques digitais.",
        "en": "Como os bombeiros, mas para ataques digitais.",
        "s": 2.083,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 44.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 43.333,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Recebe",
        "en": "Recebe",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 48.933,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "alertas de ataques e falhas",
        "en": "alertas de ataques e falhas",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 57.333,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 56.4,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Investiga",
        "en": "Investiga",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 62.0,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "o que aconteceu e o impacto",
        "en": "o que aconteceu e o impacto",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 70.4,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 69.467,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Responde",
        "en": "Responde",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 75.067,
    "w": 27.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "contém e corrige o problema",
        "en": "contém e corrige o problema",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 3,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s03_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s03_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Vulnerabilidades de rede",
        "en": "Vulnerabilidades de rede",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "03",
        "en": "03",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 26.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 25.333,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Varreduras",
        "en": "Varreduras",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 30.667,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "de vulnerabilidades",
        "en": "de vulnerabilidades",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 10.125,
    "y": 36.533,
    "w": 3.53,
    "h": 6.667,
    "src": "/deck/slides/s03_2.webp"
   },
   {
    "kind": "img",
    "x": 15.375,
    "y": 36.533,
    "w": 3.75,
    "h": 6.667,
    "src": "/deck/slides/s03_3.webp"
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 48.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 47.333,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "De rede, não de código",
        "en": "De rede, não de código",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 52.667,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "host, portas e serviços",
        "en": "host, portas e serviços",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 61.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 60.667,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Raio-X da rede",
        "en": "Raio-X da rede",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 66.0,
    "w": 24.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "revela portas e fraquezas",
        "en": "revela portas e fraquezas",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 4,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s04_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s04_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Registros de incidentes",
        "en": "Registros de incidentes",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 26.933,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 26.0,
    "w": 21.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Tickets de incidente",
        "en": "Tickets de incidente",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 31.6,
    "w": 21.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "ataques já detectados",
        "en": "ataques já detectados",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 40.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 39.333,
    "w": 21.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Vêm dos CSIRTs",
        "en": "Vêm dos CSIRTs",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 53.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 52.667,
    "w": 21.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Expõem a vítima",
        "en": "Expõem a vítima",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 58.267,
    "w": 21.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "e-mails, nomes, IPs",
        "en": "e-mails, nomes, IPs",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 9.75,
    "y": 44.933,
    "w": 7.187,
    "h": 3.467,
    "src": "/deck/slides/s04_2.webp"
   },
   {
    "kind": "img",
    "x": 18.587,
    "y": 44.933,
    "w": 6.25,
    "h": 3.467,
    "src": "/deck/slides/s04_3.webp"
   },
   {
    "kind": "img",
    "x": 26.487,
    "y": 44.933,
    "w": 4.619,
    "h": 3.467,
    "src": "/deck/slides/s04_4.webp"
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "04",
        "en": "04",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 5,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s05_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A escala do problema: vulnerabilidades",
        "en": "A escala do problema: vulnerabilidades",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 25.333,
    "w": 86.252,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "O número de vulnerabilidades cresce muito mais rápido que a capacidade de analisá-las.",
        "en": "O número de vulnerabilidades cresce muito mais rápido que a capacidade de analisá-las.",
        "s": 2.083,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 7.5,
    "y": 66.623,
    "w": 7.5,
    "h": 10.71,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 4.875,
    "y": 61.29,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "18k",
        "en": "18k",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 4.875,
    "y": 78.667,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2020",
        "en": "2020",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 18.15,
    "y": 62.694,
    "w": 7.5,
    "h": 14.639,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.525,
    "y": 57.361,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "25k",
        "en": "25k",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 15.525,
    "y": 78.667,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2022",
        "en": "2022",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 28.801,
    "y": 53.984,
    "w": 7.5,
    "h": 23.35,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 26.176,
    "y": 48.65,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "40k",
        "en": "40k",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 26.176,
    "y": 78.667,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2024",
        "en": "2024",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 39.451,
    "y": 49.058,
    "w": 7.5,
    "h": 28.275,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 36.826,
    "y": 43.725,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "48k",
        "en": "48k",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 36.826,
    "y": 78.667,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2025",
        "en": "2025",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 50.101,
    "y": 42.667,
    "w": 7.5,
    "h": 34.667,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 47.476,
    "y": 37.333,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "59k",
        "en": "59k",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 47.476,
    "y": 78.667,
    "w": 12.75,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2026*",
        "en": "2026*",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 7.5,
    "y": 84.0,
    "w": 48.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CVEs publicados por ano  (*previsão)",
        "en": "CVEs publicados por ano  (*previsão)",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 60.752,
    "y": 33.333,
    "w": 32.251,
    "h": 48.0,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#B2283C",
    "rx": 1.62
   },
   {
    "kind": "img",
    "x": 63.002,
    "y": 37.333,
    "w": 4.5,
    "h": 8.0,
    "src": "/deck/slides/s05_1.webp"
   },
   {
    "kind": "text",
    "x": 63.002,
    "y": 47.333,
    "w": 27.751,
    "h": 12.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Crise de enriquecimento da NVD/NIST (2026)",
        "en": "Crise de enriquecimento da NVD/NIST (2026)",
        "s": 1.875,
        "b": true,
        "c": "#B2283C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 63.002,
    "y": 60.667,
    "w": 27.751,
    "h": 18.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A NIST só analisa os CVEs prioritários. O resto fica sem classificação, e sobra para o CSIRT local.",
        "en": "A NIST só analisa os CVEs prioritários. O resto fica sem classificação, e sobra para o CSIRT local.",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 63.002,
    "y": 77.067,
    "w": 27.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "(NIST, 2026)",
        "en": "(NIST, 2026)",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "05",
        "en": "05",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 69.002,
    "y": 38.667,
    "w": 10.253,
    "h": 4.8,
    "src": "/deck/slides/s05_2.webp"
   }
  ]
 },
 {
  "n": 6,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s06_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.933,
    "w": 81.752,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A escala do problema: incidentes",
        "en": "A escala do problema: incidentes",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 25.333,
    "w": 86.252,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "As notificações de incidentes saltaram de milhares para milhões em duas décadas.",
        "en": "As notificações de incidentes saltaram de milhares para milhões em duas décadas.",
        "s": 2.083,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 10.125,
    "y": 77.2,
    "w": 8.625,
    "h": 0.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 8.25,
    "y": 71.867,
    "w": 12.375,
    "h": 4.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "3,1 mil",
        "en": "3,1 mil",
        "s": 1.563,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 8.25,
    "y": 79.067,
    "w": 12.375,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "1999",
        "en": "1999",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 22.876,
    "y": 65.06,
    "w": 8.625,
    "h": 12.94,
    "fill": "#96660C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 21.001,
    "y": 59.727,
    "w": 12.375,
    "h": 4.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "875 mil",
        "en": "875 mil",
        "s": 1.563,
        "b": true,
        "c": "#96660C",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 21.001,
    "y": 79.067,
    "w": 12.375,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2019",
        "en": "2019",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 35.626,
    "y": 44.0,
    "w": 8.625,
    "h": 34.0,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 33.751,
    "y": 38.667,
    "w": 12.375,
    "h": 4.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2,3 mi",
        "en": "2,3 mi",
        "s": 1.875,
        "b": true,
        "c": "#B2283C",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 33.751,
    "y": 79.067,
    "w": 12.375,
    "h": 4.533,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "2023",
        "en": "2023",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 7.5,
    "y": 84.667,
    "w": 42.001,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Notificações de incidentes ao CERT.br, por ano (CERT.br/NIC.br)",
        "en": "Notificações de incidentes ao CERT.br, por ano (CERT.br/NIC.br)",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 55.126,
    "y": 36.667,
    "w": 37.876,
    "h": 40.667,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#B2283C",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 40.0,
    "w": 32.251,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A capacidade não acompanha",
        "en": "A capacidade não acompanha",
        "s": 1.979,
        "b": true,
        "c": "#B2283C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 49.333,
    "w": 32.251,
    "h": 20.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Déficit global de ~4,8 milhões de profissionais de segurança. Cada registro tratado por uma CSIRT carrega dados pessoais a proteger.",
        "en": "Déficit global de ~4,8 milhões de profissionais de segurança. Cada registro tratado por uma CSIRT carrega dados pessoais a proteger.",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 70.0,
    "w": 32.251,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "(ISC2 Workforce Study, 2024)",
        "en": "(ISC2 Workforce Study, 2024)",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "tri",
    "x": 43.126,
    "y": 32.8,
    "w": 4.125,
    "h": 6.667,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 43.126,
    "y": 34.933,
    "w": 4.125,
    "h": 4.8,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "!",
        "en": "!",
        "s": 1.771,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "06",
        "en": "06",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 7,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s07_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s07_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Automação com IA",
        "en": "Automação com IA",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "07",
        "en": "07",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 22.667,
    "w": 31.501,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "LLMs que ",
        "en": "LLMs que ",
        "s": 2.083,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       },
       {
        "pt": "priorizam, classificam e sugerem respostas.",
        "en": "priorizam, classificam e sugerem respostas.",
        "s": 2.083,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 8,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s08_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Sensibilidade dos dados",
        "en": "Sensibilidade dos dados",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "08",
        "en": "08",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 26.933,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 26.0,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Identificadores de rede",
        "en": "Identificadores de rede",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 31.6,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "IP, hostname, certificado",
        "en": "IP, hostname, certificado",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 40.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 39.333,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Dados pessoais",
        "en": "Dados pessoais",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 44.933,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "nomes e e-mails das vítimas",
        "en": "nomes e e-mails das vítimas",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 53.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 52.667,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Perigoso se vazar",
        "en": "Perigoso se vazar",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 58.267,
    "w": 27.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "expõe a rede e fere a LGPD",
        "en": "expõe a rede e fere a LGPD",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 45.459,
    "y": 23.333,
    "w": 52.419,
    "h": 76.0,
    "src": "/deck/slides/s08_1.webp"
   }
  ]
 },
 {
  "n": 9,
  "els": [
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 22.667,
    "w": 86.252,
    "h": 0.267,
    "fill": "#D0CABA",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 26.0,
    "w": 86.252,
    "h": 19.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Como preparar esses dados para usar a IA com ",
        "en": "Como preparar esses dados para usar a IA com ",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       },
       {
        "pt": "segurança",
        "en": "segurança",
        "s": 3.958,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       },
       {
        "pt": ", em ",
        "en": ", em ",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       },
       {
        "pt": "escala",
        "en": "escala",
        "s": 3.958,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       },
       {
        "pt": ", sem perder a ",
        "en": ", sem perder a ",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       },
       {
        "pt": "utilidade",
        "en": "utilidade",
        "s": 3.958,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       },
       {
        "pt": "?",
        "en": "?",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 86.0,
    "w": 86.252,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A resposta deste trabalho: pseudonimização.",
        "en": "A resposta deste trabalho: pseudonimização.",
        "s": 2.292,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "09",
        "en": "09",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 29.738,
    "y": 45.333,
    "w": 40.501,
    "h": 40.186,
    "src": "/deck/slides/s09_0.webp"
   }
  ]
 },
 {
  "n": 10,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s10_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "O que é uma entidade?",
        "en": "O que é uma entidade?",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "10",
        "en": "10",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 54.0,
    "w": 86.252,
    "h": 13.333,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 58.0,
    "w": 80.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "host: ",
        "en": "host: ",
        "s": 2.292,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "\"100.111.20.23\"",
        "en": "\"100.111.20.23\"",
        "s": 2.292,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       },
       {
        "pt": "   →   ",
        "en": "   →   ",
        "s": 2.292,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "\"[IP_ADDRESS_a4f2b1c3]\"",
        "en": "\"[IP_ADDRESS_a4f2b1c3]\"",
        "s": 2.292,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 27.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 26.667,
    "w": 82.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Um tipo reconhecido",
        "en": "Um tipo reconhecido",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 32.267,
    "w": 82.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "um dado pessoal ou um artefato técnico",
        "en": "um dado pessoal ou um artefato técnico",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 38.933,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 38.0,
    "w": 82.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Exemplos de entidade",
        "en": "Exemplos de entidade",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 43.6,
    "w": 82.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "IP, hostname, nome, hash, certificado",
        "en": "IP, hostname, nome, hash, certificado",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 11,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s11_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Exemplo: antes e depois (Tenable)",
        "en": "Exemplo: antes e depois (Tenable)",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 28.667,
    "w": 42.001,
    "h": 52.0,
    "fill": "#FFFFFF",
    "bw": 0.208,
    "bc": "#B2283C",
    "rx": 1.463
   },
   {
    "kind": "text",
    "x": 9.0,
    "y": 31.333,
    "w": 37.501,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Original",
        "en": "Original",
        "s": 1.875,
        "b": true,
        "c": "#B2283C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 54.001,
    "y": 28.667,
    "w": 39.001,
    "h": 52.0,
    "fill": "#FFFFFF",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 1.463
   },
   {
    "kind": "text",
    "x": 56.251,
    "y": 31.333,
    "w": 37.501,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Anonimizado",
        "en": "Anonimizado",
        "s": 1.875,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "11",
        "en": "11",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.0,
    "y": 38.667,
    "w": 7.5,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "{",
        "en": "{",
        "s": 1.354,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 44.0,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"host-ip\": ",
        "en": "\"host-ip\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"100.111.20.23\",",
        "en": "\"100.111.20.23\",",
        "s": 1.354,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 49.333,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"host-fqdn\": ",
        "en": "\"host-fqdn\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"dns01.corp.br\",",
        "en": "\"dns01.corp.br\",",
        "s": 1.354,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 54.667,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"mac-address\": ",
        "en": "\"mac-address\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"00:1A:2B:3C:4D\",",
        "en": "\"00:1A:2B:3C:4D\",",
        "s": 1.354,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 60.0,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"severity\": ",
        "en": "\"severity\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"High\",",
        "en": "\"High\",",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 65.333,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"cvss3_base_score\": ",
        "en": "\"cvss3_base_score\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "7.4,",
        "en": "7.4,",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 10.875,
    "y": 70.667,
    "w": 38.251,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"port\": ",
        "en": "\"port\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "443",
        "en": "443",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.0,
    "y": 76.0,
    "w": 7.5,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "}",
        "en": "}",
        "s": 1.354,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 56.251,
    "y": 38.667,
    "w": 7.5,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "{",
        "en": "{",
        "s": 1.354,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 44.0,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"host-ip\": ",
        "en": "\"host-ip\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"[IP_ADDRESS_48624b5c]\",",
        "en": "\"[IP_ADDRESS_48624b5c]\",",
        "s": 1.354,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 49.333,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"host-fqdn\": ",
        "en": "\"host-fqdn\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"[HOSTNAME_7e9d2a]\",",
        "en": "\"[HOSTNAME_7e9d2a]\",",
        "s": 1.354,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 54.667,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"mac-address\": ",
        "en": "\"mac-address\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"[MAC_ADDRESS_c8b1]\",",
        "en": "\"[MAC_ADDRESS_c8b1]\",",
        "s": 1.354,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 60.0,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"severity\": ",
        "en": "\"severity\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "\"High\",",
        "en": "\"High\",",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 65.333,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"cvss3_base_score\": ",
        "en": "\"cvss3_base_score\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "7.4,",
        "en": "7.4,",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 58.126,
    "y": 70.667,
    "w": 36.751,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "\"port\": ",
        "en": "\"port\": ",
        "s": 1.354,
        "b": false,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "443",
        "en": "443",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 56.251,
    "y": 76.0,
    "w": 7.5,
    "h": 5.067,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "}",
        "en": "}",
        "s": 1.354,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 84.0,
    "w": 86.252,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Vermelho: sensível   ·   ",
        "en": "Vermelho: sensível   ·   ",
        "s": 1.458,
        "b": true,
        "c": "#B2283C",
        "f": "sans"
       },
       {
        "pt": "Teal: pseudonimizado   ·   ",
        "en": "Teal: pseudonimizado   ·   ",
        "s": 1.458,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       },
       {
        "pt": "Preto: preservado   ·   ",
        "en": "Preto: preservado   ·   ",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       },
       {
        "pt": "campos do Tenable (exemplos)",
        "en": "campos do Tenable (exemplos)",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 12,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s12_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "O pipeline de pseudonimização",
        "en": "O pipeline de pseudonimização",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 38.667,
    "w": 86.252,
    "h": 42.667,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.96
   },
   {
    "kind": "img",
    "x": 8.625,
    "y": 43.333,
    "w": 82.502,
    "h": 33.018,
    "src": "/deck/slides/s12_1.webp"
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "12",
        "en": "12",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 13,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s13_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Estágio 1: Entrada",
        "en": "Estágio 1: Entrada",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 25.333,
    "w": 86.252,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "O sistema lê vários formatos. Arquivos grandes são lidos em fluxo.",
        "en": "O sistema lê vários formatos. Arquivos grandes são lidos em fluxo.",
        "s": 2.292,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "13",
        "en": "13",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 7.125,
    "y": 34.0,
    "w": 22.876,
    "h": 53.333,
    "src": "/deck/slides/s13_1.webp"
   },
   {
    "kind": "img",
    "x": 40.126,
    "y": 47.333,
    "w": 46.501,
    "h": 46.14,
    "src": "/deck/slides/s13_2.webp"
   },
   {
    "kind": "text",
    "x": 40.126,
    "y": 39.333,
    "w": 46.501,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Leitura em fluxo (streaming)",
        "en": "Leitura em fluxo (streaming)",
        "s": 1.979,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 14,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s14_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Estágio 2: Detecção (NER)",
        "en": "Estágio 2: Detecção (NER)",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 19.125,
    "y": 27.333,
    "w": 73.877,
    "h": 20.667,
    "fill": "#FFFFFF",
    "bw": 0.208,
    "bc": "#96660C",
    "rx": 0.698
   },
   {
    "kind": "text",
    "x": 21.376,
    "y": 30.4,
    "w": 82.502,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Failed login from ",
        "en": "Failed login from ",
        "s": 1.979,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "100.111.20.23",
        "en": "100.111.20.23",
        "s": 1.979,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       },
       {
        "pt": "  user=",
        "en": "  user=",
        "s": 1.979,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "cristhian.kapelinski",
        "en": "cristhian.kapelinski",
        "s": 1.979,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 21.376,
    "y": 38.0,
    "w": 82.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "o NER e o RegEx reconhecem o IP e o nome como entidades",
        "en": "o NER e o RegEx reconhecem o IP e o nome como entidades",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "14",
        "en": "14",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.0,
    "y": 51.333,
    "w": 36.751,
    "h": 6.0,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Cache (vem antes)",
        "en": "Cache (vem antes)",
        "s": 1.771,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   },
   {
    "kind": "img",
    "x": 9.0,
    "y": 57.333,
    "w": 36.751,
    "h": 36.465,
    "src": "/deck/slides/s14_1.webp"
   },
   {
    "kind": "text",
    "x": 54.001,
    "y": 51.333,
    "w": 36.751,
    "h": 6.0,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "GPU no modelo NER",
        "en": "GPU no modelo NER",
        "s": 1.771,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   },
   {
    "kind": "img",
    "x": 54.001,
    "y": 57.333,
    "w": 36.751,
    "h": 36.465,
    "src": "/deck/slides/s14_2.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 27.333,
    "w": 10.5,
    "h": 21.733,
    "src": "/deck/slides/s14_3.webp"
   }
  ]
 },
 {
  "n": 15,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s15_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Estágio 3: HMAC-SHA256",
        "en": "Estágio 3: HMAC-SHA256",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 26.0,
    "w": 86.252,
    "h": 12.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Cada entidade vira um pseudônimo gerado com uma chave secreta.",
        "en": "Cada entidade vira um pseudônimo gerado com uma chave secreta.",
        "s": 2.396,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 34.933,
    "w": 26.251,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "100.111.20.23",
        "en": "100.111.20.23",
        "s": 2.292,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 29.251,
    "y": 35.2,
    "w": 4.5,
    "h": 5.6,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 34.501,
    "y": 34.667,
    "w": 31.501,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "[IP_ADDRESS",
        "en": "[IP_ADDRESS",
        "s": 2.292,
        "b": true,
        "c": "#96660C",
        "f": "mono"
       },
       {
        "pt": "_",
        "en": "_",
        "s": 2.292,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "48624b5c]",
        "en": "48624b5c]",
        "s": 2.292,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 43.333,
    "w": 57.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "o prefixo guarda o ",
        "en": "o prefixo guarda o ",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "tipo da entidade",
        "en": "tipo da entidade",
        "s": 1.667,
        "b": true,
        "c": "#96660C",
        "f": "sans"
       },
       {
        "pt": "; o resto é o ",
        "en": "; o resto é o ",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "hash gerado com a chave secreta",
        "en": "hash gerado com a chave secreta",
        "s": 1.667,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       },
       {
        "pt": ".",
        "en": ".",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "15",
        "en": "15",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 67.127,
    "y": 34.667,
    "w": 22.876,
    "h": 53.333,
    "src": "/deck/slides/s15_1.webp"
   },
   {
    "kind": "img",
    "x": 9.0,
    "y": 51.333,
    "w": 37.501,
    "h": 37.209,
    "src": "/deck/slides/s15_2.webp"
   }
  ]
 },
 {
  "n": 16,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s16_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Estágios 4 e 5: Persistência e Saída",
        "en": "Estágios 4 e 5: Persistência e Saída",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "16",
        "en": "16",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 31.333,
    "w": 10.5,
    "h": 24.267,
    "src": "/deck/slides/s16_1.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 60.667,
    "w": 10.5,
    "h": 24.267,
    "src": "/deck/slides/s16_2.webp"
   },
   {
    "kind": "text",
    "x": 19.125,
    "y": 32.0,
    "w": 52.501,
    "h": 4.8,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Persistência",
        "en": "Persistência",
        "s": 1.875,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.125,
    "y": 37.867,
    "w": 69.752,
    "h": 4.8,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "banco SQLite (tabela ",
        "en": "banco SQLite (tabela ",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "entities",
        "en": "entities",
        "s": 1.302,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       },
       {
        "pt": "): guarda o hash completo",
        "en": "): guarda o hash completo",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 19.125,
    "y": 43.2,
    "w": 10.5,
    "h": 4.0,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 19.725,
    "y": 43.2,
    "w": 9.45,
    "h": 4.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Tipo",
        "en": "Tipo",
        "s": 1.25,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 29.626,
    "y": 43.2,
    "w": 15.375,
    "h": 4.0,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 30.226,
    "y": 43.2,
    "w": 14.325,
    "h": 4.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Original",
        "en": "Original",
        "s": 1.25,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 45.001,
    "y": 43.2,
    "w": 21.376,
    "h": 4.0,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 45.601,
    "y": 43.2,
    "w": 20.326,
    "h": 4.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Pseudônimo",
        "en": "Pseudônimo",
        "s": 1.25,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 66.377,
    "y": 43.2,
    "w": 21.376,
    "h": 4.0,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 66.977,
    "y": 43.2,
    "w": 20.326,
    "h": 4.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Hash completo (64c)",
        "en": "Hash completo (64c)",
        "s": 1.25,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 19.125,
    "y": 47.2,
    "w": 10.5,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 19.725,
    "y": 47.2,
    "w": 9.45,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "IP_ADDRESS",
        "en": "IP_ADDRESS",
        "s": 1.198,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 29.626,
    "y": 47.2,
    "w": 15.375,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 30.226,
    "y": 47.2,
    "w": 14.325,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "100.111.20.23",
        "en": "100.111.20.23",
        "s": 1.198,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 45.001,
    "y": 47.2,
    "w": 21.376,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 45.601,
    "y": 47.2,
    "w": 20.326,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "[IP_ADDRESS_48624b5c]",
        "en": "[IP_ADDRESS_48624b5c]",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 66.377,
    "y": 47.2,
    "w": 21.376,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 66.977,
    "y": 47.2,
    "w": 20.326,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "48624b5c9a3f2e1d…",
        "en": "48624b5c9a3f2e1d…",
        "s": 1.198,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 19.125,
    "y": 52.133,
    "w": 10.5,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 19.725,
    "y": 52.133,
    "w": 9.45,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "HOSTNAME",
        "en": "HOSTNAME",
        "s": 1.198,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 29.626,
    "y": 52.133,
    "w": 15.375,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 30.226,
    "y": 52.133,
    "w": 14.325,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "srv-web-01",
        "en": "srv-web-01",
        "s": 1.198,
        "b": true,
        "c": "#B2283C",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 45.001,
    "y": 52.133,
    "w": 21.376,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 45.601,
    "y": 52.133,
    "w": 20.326,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "[HOSTNAME_e5c53b15]",
        "en": "[HOSTNAME_e5c53b15]",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 66.377,
    "y": 52.133,
    "w": 21.376,
    "h": 4.933,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 66.977,
    "y": 52.133,
    "w": 20.326,
    "h": 4.933,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "e5c53b15a1d2f3e4…",
        "en": "e5c53b15a1d2f3e4…",
        "s": 1.198,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.125,
    "y": 60.667,
    "w": 52.501,
    "h": 4.8,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Saída (ex.: XML)",
        "en": "Saída (ex.: XML)",
        "s": 1.875,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.125,
    "y": 66.533,
    "w": 71.252,
    "h": 4.8,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "estrutura mantida; sensíveis (teal) viram pseudônimo, o resto (preto) é preservado",
        "en": "estrutura mantida; sensíveis (teal) viram pseudônimo, o resto (preto) é preservado",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.875,
    "y": 72.267,
    "w": 72.002,
    "h": 3.733,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "<result>",
        "en": "<result>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.875,
    "y": 75.733,
    "w": 72.002,
    "h": 3.733,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "  <host>",
        "en": "  <host>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "[IP_ADDRESS_5b02f379]",
        "en": "[IP_ADDRESS_5b02f379]",
        "s": 1.302,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       },
       {
        "pt": "</host>",
        "en": "</host>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.875,
    "y": 79.2,
    "w": 72.002,
    "h": 3.733,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "  <hostname>",
        "en": "  <hostname>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "[HOSTNAME_e5c53b15]",
        "en": "[HOSTNAME_e5c53b15]",
        "s": 1.302,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       },
       {
        "pt": "</hostname>",
        "en": "</hostname>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.875,
    "y": 82.667,
    "w": 72.002,
    "h": 3.733,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "  <port>",
        "en": "  <port>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "[PORT_2edd4ed6]",
        "en": "[PORT_2edd4ed6]",
        "s": 1.302,
        "b": true,
        "c": "#0B7667",
        "f": "mono"
       },
       {
        "pt": "</port>  ",
        "en": "</port>  ",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "<cvss>",
        "en": "<cvss>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "10.0",
        "en": "10.0",
        "s": 1.302,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "</cvss>  ",
        "en": "</cvss>  ",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "<severity>",
        "en": "<severity>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       },
       {
        "pt": "Critical",
        "en": "Critical",
        "s": 1.302,
        "b": true,
        "c": "#110E09",
        "f": "mono"
       },
       {
        "pt": "</severity>",
        "en": "</severity>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 19.875,
    "y": 86.133,
    "w": 72.002,
    "h": 3.733,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "</result>",
        "en": "</result>",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 17,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s17_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "A linha de pesquisa AnonLFI",
        "en": "A linha de pesquisa AnonLFI",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 18.15,
    "y": 38.0,
    "w": 19.125,
    "h": 22.667,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#B2283C",
    "rx": 0.765
   },
   {
    "kind": "text",
    "x": 20.026,
    "y": 41.333,
    "w": 15.375,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonLFI 1.0",
        "en": "AnonLFI 1.0",
        "s": 2.083,
        "b": true,
        "c": "#564E42",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 20.026,
    "y": 48.8,
    "w": 15.375,
    "h": 10.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "primeiro pipeline",
        "en": "primeiro pipeline",
        "s": 1.302,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     },
     {
      "a": "left",
      "runs": [
       {
        "pt": "de outra equipe (Bandel et al.)",
        "en": "de outra equipe (Bandel et al.)",
        "s": 1.302,
        "b": true,
        "c": "#B2283C",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 37.576,
    "y": 46.667,
    "w": 2.55,
    "h": 4.533,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 40.426,
    "y": 38.0,
    "w": 19.125,
    "h": 22.667,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#96660C",
    "rx": 0.765
   },
   {
    "kind": "text",
    "x": 42.301,
    "y": 41.333,
    "w": 15.375,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonLFI 2.0",
        "en": "AnonLFI 2.0",
        "s": 2.083,
        "b": true,
        "c": "#96660C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 42.301,
    "y": 49.333,
    "w": 15.375,
    "h": 9.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "arquitetura extensível (WRSeg)",
        "en": "arquitetura extensível (WRSeg)",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 59.851,
    "y": 46.667,
    "w": 2.55,
    "h": 4.533,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 62.702,
    "y": 38.0,
    "w": 19.125,
    "h": 22.667,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 0.765
   },
   {
    "kind": "text",
    "x": 64.577,
    "y": 41.333,
    "w": 15.375,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonShield",
        "en": "AnonShield",
        "s": 2.083,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 64.577,
    "y": 49.333,
    "w": 15.375,
    "h": 9.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "escala (SBRC, Salão Fer.)",
        "en": "escala (SBRC, Salão Fer.)",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 21.526,
    "y": 65.333,
    "w": 12.375,
    "h": 27.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.619
   },
   {
    "kind": "img",
    "x": 22.651,
    "y": 67.333,
    "w": 10.125,
    "h": 18.0,
    "src": "/deck/slides/s17_1.webp"
   },
   {
    "kind": "text",
    "x": 21.526,
    "y": 86.0,
    "w": 12.375,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "SBSeg 2025",
        "en": "SBSeg 2025",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 43.801,
    "y": 65.333,
    "w": 12.375,
    "h": 27.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.619
   },
   {
    "kind": "img",
    "x": 44.926,
    "y": 67.333,
    "w": 10.125,
    "h": 18.0,
    "src": "/deck/slides/s17_2.webp"
   },
   {
    "kind": "text",
    "x": 43.801,
    "y": 86.0,
    "w": 12.375,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "WRSeg 2025",
        "en": "WRSeg 2025",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 66.077,
    "y": 65.333,
    "w": 12.375,
    "h": 27.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.619
   },
   {
    "kind": "img",
    "x": 67.202,
    "y": 67.333,
    "w": 10.125,
    "h": 18.0,
    "src": "/deck/slides/s17_3.webp"
   },
   {
    "kind": "text",
    "x": 66.077,
    "y": 86.0,
    "w": 12.375,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "SBRC 2026",
        "en": "SBRC 2026",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "17",
        "en": "17",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 18,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s18_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Evolução da linha AnonLFI",
        "en": "Evolução da linha AnonLFI",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 25.333,
    "w": 86.252,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Linhas de código e número de módulos por versão.",
        "en": "Linhas de código e número de módulos por versão.",
        "s": 2.292,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 17.749,
    "y": 78.139,
    "w": 16.5,
    "h": 2.527,
    "fill": "#564E42",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 14.749,
    "y": 71.206,
    "w": 22.501,
    "h": 5.6,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "361 linhas",
        "en": "361 linhas",
        "s": 2.396,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 14.749,
    "y": 82.533,
    "w": 22.501,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "AnonLFI 1.0",
        "en": "AnonLFI 1.0",
        "s": 2.083,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     },
     {
      "a": "center",
      "runs": [
       {
        "pt": "monolítico (1 módulo)",
        "en": "monolítico (1 módulo)",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 41.75,
    "y": 73.862,
    "w": 16.5,
    "h": 6.805,
    "fill": "#96660C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.75,
    "y": 66.929,
    "w": 22.501,
    "h": 5.6,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "972 linhas",
        "en": "972 linhas",
        "s": 2.396,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 38.75,
    "y": 82.533,
    "w": 22.501,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "AnonLFI 2.0",
        "en": "AnonLFI 2.0",
        "s": 2.083,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     },
     {
      "a": "center",
      "runs": [
       {
        "pt": "5 módulos",
        "en": "5 módulos",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.75,
    "y": 42.667,
    "w": 16.5,
    "h": 38.0,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 62.75,
    "y": 35.733,
    "w": 22.501,
    "h": 5.6,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "5.428 linhas",
        "en": "5.428 linhas",
        "s": 2.396,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 62.75,
    "y": 82.533,
    "w": 22.501,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "AnonShield",
        "en": "AnonShield",
        "s": 2.083,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     },
     {
      "a": "center",
      "runs": [
       {
        "pt": "17 módulos",
        "en": "17 módulos",
        "s": 1.667,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "18",
        "en": "18",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 19,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s19_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s19_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Motivação: a escala operacional",
        "en": "Motivação: a escala operacional",
        "s": 2.917,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "19",
        "en": "19",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 27.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 26.667,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "70.951 vulnerabilidades",
        "en": "70.951 vulnerabilidades",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 32.267,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "do CAIS/RNP",
        "en": "do CAIS/RNP",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 41.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 40.667,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Antes: +92 horas",
        "en": "Antes: +92 horas",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 46.267,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "inviável em escala",
        "en": "inviável em escala",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 55.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 54.667,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Daí o AnonShield",
        "en": "Daí o AnonShield",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 60.267,
    "w": 24.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "feito para escalar",
        "en": "feito para escalar",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 20,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s20_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Conjuntos de dados",
        "en": "Conjuntos de dados",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "20",
        "en": "20",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.801,
    "y": 45.6,
    "w": 5.55,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.801,
    "y": 57.6,
    "w": 5.55,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.426,
    "y": 45.6,
    "w": 7.575,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.426,
    "y": 57.6,
    "w": 7.575,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 36.0,
    "w": 7.5,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 36.0,
    "w": 5.85,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Base",
        "en": "Base",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 36.0,
    "w": 22.876,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 36.0,
    "w": 21.226,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Origem",
        "en": "Origem",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 36.0,
    "w": 16.125,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 36.0,
    "w": 14.475,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Formatos",
        "en": "Formatos",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 36.0,
    "w": 10.875,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 36.0,
    "w": 9.225,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Arquivos",
        "en": "Arquivos",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 36.0,
    "w": 10.5,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 36.0,
    "w": 8.85,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Tamanho",
        "en": "Tamanho",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 36.0,
    "w": 17.625,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 36.0,
    "w": 15.975,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Finalidade",
        "en": "Finalidade",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 45.6,
    "w": 7.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 45.6,
    "w": 5.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "D1",
        "en": "D1",
        "s": 1.458,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 45.6,
    "w": 22.876,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 45.6,
    "w": 21.226,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "OpenVAS (laboratório VulnLab)",
        "en": "OpenVAS (laboratório VulnLab)",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 45.6,
    "w": 16.125,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 45.6,
    "w": 14.475,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CSV, TXT, PDF, XML",
        "en": "CSV, TXT, PDF, XML",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 45.6,
    "w": 10.875,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 45.6,
    "w": 9.225,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 45.6,
    "w": 10.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 45.6,
    "w": 8.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "9 a 34 MB",
        "en": "9 a 34 MB",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 45.6,
    "w": 17.625,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 45.6,
    "w": 15.975,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Acurácia e desempenho",
        "en": "Acurácia e desempenho",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 57.6,
    "w": 7.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 57.6,
    "w": 5.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "D1C",
        "en": "D1C",
        "s": 1.458,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 57.6,
    "w": 22.876,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 57.6,
    "w": 21.226,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Conversão do D1 (outros formatos)",
        "en": "Conversão do D1 (outros formatos)",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 57.6,
    "w": 16.125,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 57.6,
    "w": 14.475,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "XLSX, DOCX, PDF-img, JSON",
        "en": "XLSX, DOCX, PDF-img, JSON",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 57.6,
    "w": 10.875,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 57.6,
    "w": 9.225,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130",
        "en": "130",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 57.6,
    "w": 10.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 57.6,
    "w": 8.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "até 1,5 GB",
        "en": "até 1,5 GB",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 57.6,
    "w": 17.625,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 57.6,
    "w": 15.975,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Acurácia e desempenho",
        "en": "Acurácia e desempenho",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 21,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s21_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Laboratório de serviços vulneráveis",
        "en": "Laboratório de serviços vulneráveis",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "21",
        "en": "21",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 22.933,
    "w": 88.502,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "VulnLab: 130 containers Docker vulneráveis, em 11 categorias de serviços.",
        "en": "VulnLab: 130 containers Docker vulneráveis, em 11 categorias de serviços.",
        "s": 1.875,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 5.625,
    "y": 30.4,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Aplicações web vulneráveis · 21",
        "en": "Aplicações web vulneráveis · 21",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 8.475,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_1.webp"
   },
   {
    "kind": "text",
    "x": 5.25,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "OWASP",
        "en": "OWASP",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 16.515,
    "y": 34.8,
    "w": 4.471,
    "h": 4.533,
    "src": "/deck/slides/s21_2.webp"
   },
   {
    "kind": "text",
    "x": 14.25,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "DVWA",
        "en": "DVWA",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 5.625,
    "y": 46.0,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Rede e infraestrutura · 19",
        "en": "Rede e infraestrutura · 19",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 5.91,
    "y": 50.4,
    "w": 7.68,
    "h": 4.533,
    "src": "/deck/slides/s21_3.webp"
   },
   {
    "kind": "text",
    "x": 5.25,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "OpenSSH",
        "en": "OpenSSH",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 15.519,
    "y": 50.4,
    "w": 6.464,
    "h": 4.533,
    "src": "/deck/slides/s21_4.webp"
   },
   {
    "kind": "text",
    "x": 14.25,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "OpenLDAP",
        "en": "OpenLDAP",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 26.476,
    "y": 50.4,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_5.webp"
   },
   {
    "kind": "text",
    "x": 23.251,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Memcached",
        "en": "Memcached",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 5.625,
    "y": 61.6,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Bancos de dados · 17",
        "en": "Bancos de dados · 17",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 8.475,
    "y": 66.0,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_6.webp"
   },
   {
    "kind": "text",
    "x": 5.25,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "MySQL",
        "en": "MySQL",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 17.475,
    "y": 66.0,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_7.webp"
   },
   {
    "kind": "text",
    "x": 14.25,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "PostgreSQL",
        "en": "PostgreSQL",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 26.476,
    "y": 66.0,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_8.webp"
   },
   {
    "kind": "text",
    "x": 23.251,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "MongoDB",
        "en": "MongoDB",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 5.625,
    "y": 77.2,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Servidores web e de aplicação · 17",
        "en": "Servidores web e de aplicação · 17",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 8.475,
    "y": 81.6,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_9.webp"
   },
   {
    "kind": "text",
    "x": 5.25,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Apache",
        "en": "Apache",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 17.475,
    "y": 81.6,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_10.webp"
   },
   {
    "kind": "text",
    "x": 14.25,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Nginx",
        "en": "Nginx",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 26.476,
    "y": 81.6,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_11.webp"
   },
   {
    "kind": "text",
    "x": 23.251,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Tomcat",
        "en": "Tomcat",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 36.751,
    "y": 30.4,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Linguagens e runtimes · 12",
        "en": "Linguagens e runtimes · 12",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 39.601,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_12.webp"
   },
   {
    "kind": "text",
    "x": 36.376,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Python",
        "en": "Python",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 48.601,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_13.webp"
   },
   {
    "kind": "text",
    "x": 45.376,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Node.js",
        "en": "Node.js",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 57.601,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_14.webp"
   },
   {
    "kind": "text",
    "x": 54.376,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "PHP",
        "en": "PHP",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 36.751,
    "y": 46.0,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CMS e plataformas web · 11",
        "en": "CMS e plataformas web · 11",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 39.601,
    "y": 50.4,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_15.webp"
   },
   {
    "kind": "text",
    "x": 36.376,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "WordPress",
        "en": "WordPress",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 48.601,
    "y": 50.4,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_16.webp"
   },
   {
    "kind": "text",
    "x": 45.376,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Drupal",
        "en": "Drupal",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 57.601,
    "y": 50.4,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_17.webp"
   },
   {
    "kind": "text",
    "x": 54.376,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "GitLab",
        "en": "GitLab",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 36.751,
    "y": 61.6,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "DevOps e CI/CD · 9",
        "en": "DevOps e CI/CD · 9",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 39.721,
    "y": 66.0,
    "w": 2.311,
    "h": 4.533,
    "src": "/deck/slides/s21_18.webp"
   },
   {
    "kind": "text",
    "x": 36.376,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Jenkins",
        "en": "Jenkins",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 48.601,
    "y": 66.0,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_19.webp"
   },
   {
    "kind": "text",
    "x": 45.376,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "SonarQube",
        "en": "SonarQube",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 57.432,
    "y": 66.0,
    "w": 2.889,
    "h": 4.533,
    "src": "/deck/slides/s21_20.webp"
   },
   {
    "kind": "text",
    "x": 54.376,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Nexus",
        "en": "Nexus",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 36.751,
    "y": 77.2,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Sistemas operacionais · 8",
        "en": "Sistemas operacionais · 8",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 39.549,
    "y": 81.6,
    "w": 2.654,
    "h": 4.533,
    "src": "/deck/slides/s21_21.webp"
   },
   {
    "kind": "text",
    "x": 36.376,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Ubuntu",
        "en": "Ubuntu",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 48.85,
    "y": 81.6,
    "w": 2.052,
    "h": 4.533,
    "src": "/deck/slides/s21_22.webp"
   },
   {
    "kind": "text",
    "x": 45.376,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Debian",
        "en": "Debian",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 57.601,
    "y": 81.6,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_23.webp"
   },
   {
    "kind": "text",
    "x": 54.376,
    "y": 86.8,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "CentOS",
        "en": "CentOS",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 67.877,
    "y": 30.4,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Monitoramento e logging · 6",
        "en": "Monitoramento e logging · 6",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 70.727,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_24.webp"
   },
   {
    "kind": "text",
    "x": 67.502,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Grafana",
        "en": "Grafana",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 79.727,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_25.webp"
   },
   {
    "kind": "text",
    "x": 76.502,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Kibana",
        "en": "Kibana",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 88.727,
    "y": 34.8,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_26.webp"
   },
   {
    "kind": "text",
    "x": 85.502,
    "y": 40.0,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Prometheus",
        "en": "Prometheus",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 67.877,
    "y": 46.0,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Mensageria e streaming · 5",
        "en": "Mensageria e streaming · 5",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 70.727,
    "y": 50.4,
    "w": 2.55,
    "h": 4.533,
    "src": "/deck/slides/s21_27.webp"
   },
   {
    "kind": "text",
    "x": 67.502,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "RabbitMQ",
        "en": "RabbitMQ",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 80.225,
    "y": 50.4,
    "w": 1.554,
    "h": 4.533,
    "src": "/deck/slides/s21_28.webp"
   },
   {
    "kind": "text",
    "x": 76.502,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Kafka",
        "en": "Kafka",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 88.448,
    "y": 50.4,
    "w": 3.109,
    "h": 4.533,
    "src": "/deck/slides/s21_29.webp"
   },
   {
    "kind": "text",
    "x": 85.502,
    "y": 55.6,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "ActiveMQ",
        "en": "ActiveMQ",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 67.877,
    "y": 61.6,
    "w": 29.626,
    "h": 3.467,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CVEs específicos · 5",
        "en": "CVEs específicos · 5",
        "s": 1.198,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 68.922,
    "y": 66.0,
    "w": 6.159,
    "h": 4.533,
    "src": "/deck/slides/s21_30.webp"
   },
   {
    "kind": "text",
    "x": 67.502,
    "y": 71.2,
    "w": 9.0,
    "h": 2.133,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Log4Shell",
        "en": "Log4Shell",
        "s": 0.833,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.15,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 22,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s22_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.933,
    "w": 81.752,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Varredura com OpenVAS",
        "en": "Varredura com OpenVAS",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 25.333,
    "w": 86.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Cada container é varrido com OpenVAS/GVM (Greenbone); os relatórios formam o D1.",
        "en": "Cada container é varrido com OpenVAS/GVM (Greenbone); os relatórios formam o D1.",
        "s": 2.083,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 5.625,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 5.625,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Cria alvo",
        "en": "Cria alvo",
        "s": 1.406,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 20.551,
    "y": 39.733,
    "w": 1.95,
    "h": 3.2,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 22.726,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 22.726,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Cria tarefa",
        "en": "Cria tarefa",
        "s": 1.406,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 37.651,
    "y": 39.733,
    "w": 1.95,
    "h": 3.2,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 39.826,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 39.826,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Varre",
        "en": "Varre",
        "s": 1.406,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 54.751,
    "y": 39.733,
    "w": 1.95,
    "h": 3.2,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.926,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.926,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Monitora (30s)",
        "en": "Monitora (30s)",
        "s": 1.406,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "arrow",
    "x": 71.852,
    "y": 39.733,
    "w": 1.95,
    "h": 3.2,
    "fill": "#B2283C",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.027,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 74.027,
    "y": 36.667,
    "w": 14.625,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Baixa relatório",
        "en": "Baixa relatório",
        "s": 1.406,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 76.667,
    "w": 86.252,
    "h": 13.333,
    "fill": "#EBE6D9",
    "bw": 0.156,
    "bc": "#0B7667",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.0,
    "y": 79.733,
    "w": 82.502,
    "h": 6.667,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "~14 h",
        "en": "~14 h",
        "s": 1.771,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       },
       {
        "pt": " de varredura total     ",
        "en": " de varredura total     ",
        "s": 1.771,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "520",
        "en": "520",
        "s": 1.771,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       },
       {
        "pt": " relatórios  (130 alvos × 4 formatos: PDF, XML, CSV, TXT)",
        "en": " relatórios  (130 alvos × 4 formatos: PDF, XML, CSV, TXT)",
        "s": 1.771,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 54.133,
    "w": 1.125,
    "h": 2.0,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.525,
    "y": 53.333,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "OpenVAS/GVM (Greenbone)",
        "en": "OpenVAS/GVM (Greenbone)",
        "s": 1.615,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.525,
    "y": 57.467,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "motor de varredura de vulnerabilidades",
        "en": "motor de varredura de vulnerabilidades",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 50.626,
    "y": 54.133,
    "w": 1.125,
    "h": 2.0,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 53.026,
    "y": 53.333,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Perfil Full and fast",
        "en": "Perfil Full and fast",
        "s": 1.615,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 53.026,
    "y": 57.467,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "~30 a 60 min por host",
        "en": "~30 a 60 min por host",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 64.133,
    "w": 1.125,
    "h": 2.0,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.525,
    "y": 63.333,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Cobertura de portas",
        "en": "Cobertura de portas",
        "s": 1.615,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.525,
    "y": 67.467,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "todas as portas IANA atribuídas (TCP e UDP)",
        "en": "todas as portas IANA atribuídas (TCP e UDP)",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 50.626,
    "y": 64.133,
    "w": 1.125,
    "h": 2.0,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 53.026,
    "y": 63.333,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "130 alvos",
        "en": "130 alvos",
        "s": 1.615,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 53.026,
    "y": 67.467,
    "w": 39.751,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "cada container do VulnLab é varrido",
        "en": "cada container do VulnLab é varrido",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 87.875,
    "y": 12.667,
    "w": 4.378,
    "h": 8.267,
    "src": "/deck/slides/s22_1.webp"
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "22",
        "en": "22",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 23,
  "els": [
   {
    "kind": "img",
    "x": 0.0,
    "y": 0.0,
    "w": 100.0,
    "h": 100.0,
    "src": "/deck/slides/s23_0.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s23_1.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Metodologia",
        "en": "Metodologia",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "23",
        "en": "23",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 26.933,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 26.0,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Amostra: 67 de 6.472 (D1)",
        "en": "Amostra: 67 de 6.472 (D1)",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 31.6,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "90% confiança, 3 especialistas",
        "en": "90% confiança, 3 especialistas",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 40.267,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 39.333,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "13 tipos de entidades",
        "en": "13 tipos de entidades",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 44.933,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "avaliados manualmente",
        "en": "avaliados manualmente",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "oval",
    "x": 7.125,
    "y": 53.6,
    "w": 1.2,
    "h": 2.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 52.667,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Métricas",
        "en": "Métricas",
        "s": 1.875,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 58.267,
    "w": 24.751,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Precisão, Recall (crítica), F1",
        "en": "Precisão, Recall (crítica), F1",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.225,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 24,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s24_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Acurácia",
        "en": "Acurácia",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 33.333,
    "w": 30.001,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 33.333,
    "w": 27.901,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Versão",
        "en": "Versão",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 36.751,
    "y": 33.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 37.801,
    "y": 33.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Precisão",
        "en": "Precisão",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 55.501,
    "y": 33.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.551,
    "y": 33.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Recall",
        "en": "Recall",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.252,
    "y": 33.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.302,
    "y": 33.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "F1",
        "en": "F1",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 42.667,
    "w": 30.001,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 42.667,
    "w": 27.901,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonLFI 1.0",
        "en": "AnonLFI 1.0",
        "s": 1.563,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 36.751,
    "y": 42.667,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 37.801,
    "y": 42.667,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "32,4%",
        "en": "32,4%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 55.501,
    "y": 42.667,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.551,
    "y": 42.667,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "18,8%",
        "en": "18,8%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.252,
    "y": 42.667,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.302,
    "y": 42.667,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "23,8%",
        "en": "23,8%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 52.0,
    "w": 30.001,
    "h": 9.333,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 52.0,
    "w": 27.901,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonLFI 2.0",
        "en": "AnonLFI 2.0",
        "s": 1.563,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 36.751,
    "y": 52.0,
    "w": 18.75,
    "h": 9.333,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 37.801,
    "y": 52.0,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "80,9%",
        "en": "80,9%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 55.501,
    "y": 52.0,
    "w": 18.75,
    "h": 9.333,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.551,
    "y": 52.0,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "40,7%",
        "en": "40,7%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.252,
    "y": 52.0,
    "w": 18.75,
    "h": 9.333,
    "fill": "#FFFFFF",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.302,
    "y": 52.0,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "54,2%",
        "en": "54,2%",
        "s": 1.563,
        "b": false,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 61.333,
    "w": 30.001,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 61.333,
    "w": 27.901,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "AnonShield (standalone)",
        "en": "AnonShield (standalone)",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 36.751,
    "y": 61.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 37.801,
    "y": 61.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "91,7%",
        "en": "91,7%",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 55.501,
    "y": 61.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.551,
    "y": 61.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "96,1%",
        "en": "96,1%",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.252,
    "y": 61.333,
    "w": 18.75,
    "h": 9.333,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.302,
    "y": 61.333,
    "w": 16.65,
    "h": 9.333,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "93,8%",
        "en": "93,8%",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "24",
        "en": "24",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 79.333,
    "w": 86.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Comparação na estratégia standalone (detecção própria do AnonShield: NER + RegEx). Modelo NER: SecureModernBERT.",
        "en": "Comparação na estratégia standalone (detecção própria do AnonShield: NER + RegEx). Modelo NER: SecureModernBERT.",
        "s": 1.354,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 25,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s25_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Conjuntos de dados",
        "en": "Conjuntos de dados",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.801,
    "y": 45.6,
    "w": 5.55,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.801,
    "y": 57.6,
    "w": 5.55,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.426,
    "y": 45.6,
    "w": 7.575,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.426,
    "y": 57.6,
    "w": 7.575,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 36.0,
    "w": 7.5,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 36.0,
    "w": 5.85,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Base",
        "en": "Base",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 36.0,
    "w": 22.876,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 36.0,
    "w": 21.226,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Origem",
        "en": "Origem",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 36.0,
    "w": 16.125,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 36.0,
    "w": 14.475,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Formatos",
        "en": "Formatos",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 36.0,
    "w": 10.875,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 36.0,
    "w": 9.225,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Arquivos",
        "en": "Arquivos",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 36.0,
    "w": 10.5,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 36.0,
    "w": 8.85,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Tamanho",
        "en": "Tamanho",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 36.0,
    "w": 17.625,
    "h": 9.6,
    "fill": "#0B7667",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 36.0,
    "w": 15.975,
    "h": 9.6,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Finalidade",
        "en": "Finalidade",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 45.6,
    "w": 7.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 45.6,
    "w": 5.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "D2",
        "en": "D2",
        "s": 1.458,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 45.6,
    "w": 22.876,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 45.6,
    "w": 21.226,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Tenable (CAIS/RNP, privado)",
        "en": "Tenable (CAIS/RNP, privado)",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 45.6,
    "w": 16.125,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 45.6,
    "w": 14.475,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CSV, JSON",
        "en": "CSV, JSON",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 45.6,
    "w": 10.875,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 45.6,
    "w": 9.225,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 45.6,
    "w": 10.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 45.6,
    "w": 8.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "550 MB",
        "en": "550 MB",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 45.6,
    "w": 17.625,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 45.6,
    "w": 15.975,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Desempenho",
        "en": "Desempenho",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 57.6,
    "w": 7.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 7.8,
    "y": 57.6,
    "w": 5.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "D3",
        "en": "D3",
        "s": 1.458,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 14.25,
    "y": 57.6,
    "w": 22.876,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 15.3,
    "y": 57.6,
    "w": 21.226,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Sintético (gêmeo público do D2)",
        "en": "Sintético (gêmeo público do D2)",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 37.126,
    "y": 57.6,
    "w": 16.125,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 38.176,
    "y": 57.6,
    "w": 14.475,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "CSV, JSON",
        "en": "CSV, JSON",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 53.251,
    "y": 57.6,
    "w": 10.875,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 54.301,
    "y": 57.6,
    "w": 9.225,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "1",
        "en": "1",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 64.127,
    "y": 57.6,
    "w": 10.5,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.177,
    "y": 57.6,
    "w": 8.85,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "445 MB",
        "en": "445 MB",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.627,
    "y": 57.6,
    "w": 17.625,
    "h": 12.0,
    "fill": "#EBE6D9",
    "bw": 0.078,
    "bc": "#D0CABA",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 75.677,
    "y": 57.6,
    "w": 15.975,
    "h": 12.0,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Desempenho",
        "en": "Desempenho",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "25",
        "en": "25",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.75,
    "mt": 0.375
   }
  ]
 },
 {
  "n": 26,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s26_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Desempenho em escala operacional",
        "en": "Desempenho em escala operacional",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 51.333,
    "w": 42.001,
    "h": 26.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "738×",
        "en": "738×",
        "s": 12.5,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 7.125,
    "y": 78.0,
    "w": 46.501,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "speedup sobre o AnonLFI 2.0",
        "en": "speedup sobre o AnonLFI 2.0",
        "s": 2.188,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 52.876,
    "y": 39.333,
    "w": 40.126,
    "h": 19.333,
    "fill": "#EBE6D9",
    "bw": 0.229,
    "bc": "#B2283C",
    "rx": 0.761
   },
   {
    "kind": "text",
    "x": 55.126,
    "y": 41.6,
    "w": 36.001,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "ANTES  (AnonLFI 2.0, estimado)",
        "en": "ANTES  (AnonLFI 2.0, estimado)",
        "s": 1.563,
        "b": true,
        "c": "#B2283C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.126,
    "y": 46.667,
    "w": 36.001,
    "h": 9.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "~92 horas",
        "en": "~92 horas",
        "s": 3.75,
        "b": true,
        "c": "#B2283C",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 52.876,
    "y": 62.667,
    "w": 40.126,
    "h": 19.333,
    "fill": "#EBE6D9",
    "bw": 0.229,
    "bc": "#0B7667",
    "rx": 0.761
   },
   {
    "kind": "text",
    "x": 55.126,
    "y": 64.933,
    "w": 36.001,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "DEPOIS  (AnonShield)",
        "en": "DEPOIS  (AnonShield)",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 55.126,
    "y": 70.0,
    "w": 36.001,
    "h": 9.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "7,5 minutos",
        "en": "7,5 minutos",
        "s": 3.75,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "26",
        "en": "26",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 27,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s27_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Reconhecimento",
        "en": "Reconhecimento",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 33.001,
    "y": 47.333,
    "w": 59.251,
    "h": 10.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Melhor Artefato do SBRC 2026",
        "en": "Melhor Artefato do SBRC 2026",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 33.001,
    "y": 60.667,
    "w": 59.251,
    "h": 8.0,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Selecionado entre os 65 artefatos avaliados no evento.",
        "en": "Selecionado entre os 65 artefatos avaliados no evento.",
        "s": 2.188,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "27",
        "en": "27",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 43.876,
    "y": 69.333,
    "w": 8.25,
    "h": 14.667,
    "src": "/deck/slides/s27_1.webp"
   },
   {
    "kind": "img",
    "x": 53.626,
    "y": 69.333,
    "w": 8.25,
    "h": 14.667,
    "src": "/deck/slides/s27_2.webp"
   },
   {
    "kind": "img",
    "x": 63.377,
    "y": 69.333,
    "w": 8.25,
    "h": 14.667,
    "src": "/deck/slides/s27_3.webp"
   },
   {
    "kind": "img",
    "x": 73.127,
    "y": 69.333,
    "w": 8.25,
    "h": 14.667,
    "src": "/deck/slides/s27_4.webp"
   },
   {
    "kind": "text",
    "x": 33.001,
    "y": 86.0,
    "w": 59.251,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Selos de artefato concedidos",
        "en": "Selos de artefato concedidos",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 49.501,
    "y": 21.333,
    "w": 26.251,
    "h": 23.294,
    "src": "/deck/slides/s27_5.webp"
   },
   {
    "kind": "img",
    "x": 6.75,
    "y": 22.0,
    "w": 22.501,
    "h": 56.581,
    "src": "/deck/slides/s27_6.webp"
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 22.0,
    "w": 22.501,
    "h": 56.581,
    "fill": null,
    "bw": 0.104,
    "bc": "#564E42",
    "rx": 0
   },
   {
    "kind": "img",
    "x": 7.125,
    "y": 80.267,
    "w": 6.15,
    "h": 10.933,
    "src": "/deck/slides/s27_7.webp"
   },
   {
    "kind": "text",
    "x": 14.25,
    "y": 81.6,
    "w": 18.0,
    "h": 9.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Resultados da avaliação de artefatos (CTA)",
        "en": "Resultados da avaliação de artefatos (CTA)",
        "s": 1.146,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.3,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 28,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s28_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Utilidade analítica dos dados",
        "en": "Utilidade analítica dos dados",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "28",
        "en": "28",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 24.667,
    "w": 86.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Os dados pseudonimizados já sustentam pesquisa publicada:",
        "en": "Os dados pseudonimizados já sustentam pesquisa publicada:",
        "s": 1.875,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 34.0,
    "w": 86.252,
    "h": 25.6,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 36.267,
    "w": 65.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Severo et al. (2025)",
        "en": "Severo et al. (2025)",
        "s": 2.188,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 43.2,
    "w": 65.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Classificação automatizada de incidentes em SOCs com LLMs e engenharia de prompt.",
        "en": "Classificação automatizada de incidentes em SOCs com LLMs e engenharia de prompt.",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 79.127,
    "y": 38.933,
    "w": 9.75,
    "h": 17.333,
    "src": "/deck/slides/s28_1.webp"
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 61.067,
    "w": 86.252,
    "h": 25.6,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 63.333,
    "w": 65.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Almeida et al. (2025)",
        "en": "Almeida et al. (2025)",
        "s": 2.188,
        "b": true,
        "c": "#0B7667",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 70.267,
    "w": 65.252,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Modelos de linguagem on-premise vs. comerciais para classificar incidentes em CSIRTs.",
        "en": "Modelos de linguagem on-premise vs. comerciais para classificar incidentes em CSIRTs.",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 79.127,
    "y": 66.0,
    "w": 9.75,
    "h": 17.333,
    "src": "/deck/slides/s28_2.webp"
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 52.667,
    "w": 66.752,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Melhor resultado: ",
        "en": "Melhor resultado: ",
        "s": 1.563,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "92,27% de acurácia",
        "en": "92,27% de acurácia",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       },
       {
        "pt": "  (Gemini 2 + Progressive-Hint Prompting)",
        "en": "  (Gemini 2 + Progressive-Hint Prompting)",
        "s": 1.563,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 9.75,
    "y": 79.733,
    "w": 66.752,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "On-premise ",
        "en": "On-premise ",
        "s": 1.563,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": "~60%",
        "en": "~60%",
        "s": 1.563,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       },
       {
        "pt": " vs. ",
        "en": " vs. ",
        "s": 1.563,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       },
       {
        "pt": ">90%",
        "en": ">90%",
        "s": 1.563,
        "b": true,
        "c": "#B2283C",
        "f": "sans"
       },
       {
        "pt": " dos comerciais",
        "en": " dos comerciais",
        "s": 1.563,
        "b": false,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.375,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 29,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s29_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Trabalhos futuros (TCC II)",
        "en": "Trabalhos futuros (TCC II)",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 28.0,
    "w": 86.252,
    "h": 16.0,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Avaliação comparativa entre dados pseudonimizados e originais, medindo o equilíbrio entre ",
        "en": "Avaliação comparativa entre dados pseudonimizados e originais, medindo o equilíbrio entre ",
        "s": 2.5,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       },
       {
        "pt": "privacidade e utilidade",
        "en": "privacidade e utilidade",
        "s": 2.5,
        "b": true,
        "c": "#0B7667",
        "f": "sans"
       },
       {
        "pt": " na classificação de vulnerabilidades e incidentes com modelos de linguagem.",
        "en": " na classificação de vulnerabilidades e incidentes com modelos de linguagem.",
        "s": 2.5,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 87.2,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "29",
        "en": "29",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 47.333,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Atividade",
        "en": "Atividade",
        "s": 1.667,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 47.251,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Ago",
        "en": "Ago",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 56.401,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Set",
        "en": "Set",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 65.552,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Out",
        "en": "Out",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 74.702,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Nov",
        "en": "Nov",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 83.852,
    "y": 47.333,
    "w": 8.7,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "Dez",
        "en": "Dez",
        "s": 1.563,
        "b": true,
        "c": "#FFFFFF",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 54.133,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 54.133,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 54.133,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 54.133,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 54.133,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 53.467,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Preparação das bases e tarefas downstream",
        "en": "Preparação das bases e tarefas downstream",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 60.267,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 60.267,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 60.267,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 60.267,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 60.267,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 59.6,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Implementação do pipeline de utilidade",
        "en": "Implementação do pipeline de utilidade",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 66.4,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 66.4,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 66.4,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 66.4,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 66.4,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 65.733,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Ajuste fino com preservação de privacidade",
        "en": "Ajuste fino com preservação de privacidade",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 72.533,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 72.533,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 72.533,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 72.533,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 72.533,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 71.867,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Execução de experimentos e análise",
        "en": "Execução de experimentos e análise",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 47.251,
    "y": 78.667,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 56.401,
    "y": 78.667,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 65.552,
    "y": 78.667,
    "w": 8.7,
    "h": 4.8,
    "fill": "#EBE6D9",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 74.702,
    "y": 78.667,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 83.852,
    "y": 78.667,
    "w": 8.7,
    "h": 4.8,
    "fill": "#0B7667",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 78.0,
    "w": 39.751,
    "h": 6.133,
    "anchor": "center",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Redação e revisão do artigo final",
        "en": "Redação e revisão do artigo final",
        "s": 1.458,
        "b": true,
        "c": "#110E09",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.45,
    "mt": 0.0
   }
  ]
 },
 {
  "n": 30,
  "els": [
   {
    "kind": "img",
    "x": 6.75,
    "y": 11.2,
    "w": 4.65,
    "h": 8.267,
    "src": "/deck/slides/s30_0.webp"
   },
   {
    "kind": "text",
    "x": 12.9,
    "y": 10.4,
    "w": 80.102,
    "h": 13.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Artigos e materiais",
        "en": "Artigos e materiais",
        "s": 3.958,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 34.667,
    "w": 13.5,
    "h": 29.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.675
   },
   {
    "kind": "img",
    "x": 7.875,
    "y": 36.667,
    "w": 11.25,
    "h": 20.0,
    "src": "/deck/slides/s30_1.webp"
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 57.333,
    "w": 13.5,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "SBSeg 2025",
        "en": "SBSeg 2025",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 22.501,
    "y": 34.667,
    "w": 13.5,
    "h": 29.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.675
   },
   {
    "kind": "img",
    "x": 23.626,
    "y": 36.667,
    "w": 11.25,
    "h": 20.0,
    "src": "/deck/slides/s30_2.webp"
   },
   {
    "kind": "text",
    "x": 22.501,
    "y": 57.333,
    "w": 13.5,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "WRSeg 2025",
        "en": "WRSeg 2025",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 38.251,
    "y": 34.667,
    "w": 13.5,
    "h": 29.6,
    "fill": "#FFFFFF",
    "bw": 0.125,
    "bc": "#D0CABA",
    "rx": 0.675
   },
   {
    "kind": "img",
    "x": 39.376,
    "y": 36.667,
    "w": 11.25,
    "h": 20.0,
    "src": "/deck/slides/s30_3.webp"
   },
   {
    "kind": "text",
    "x": 38.251,
    "y": 57.333,
    "w": 13.5,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "center",
      "runs": [
       {
        "pt": "SBRC 2026",
        "en": "SBRC 2026",
        "s": 1.354,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 72.002,
    "y": 34.667,
    "w": 15.9,
    "h": 29.067,
    "fill": "#EBE6D9",
    "bw": 0.208,
    "bc": "#0B7667",
    "rx": 0.954
   },
   {
    "kind": "img",
    "x": 73.877,
    "y": 38.0,
    "w": 4.5,
    "h": 8.0,
    "src": "/deck/slides/s30_4.webp"
   },
   {
    "kind": "text",
    "x": 73.502,
    "y": 47.333,
    "w": 13.125,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "anonshield.org",
        "en": "anonshield.org",
        "s": 1.563,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 73.502,
    "y": 52.667,
    "w": 13.125,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "código e artefatos",
        "en": "código e artefatos",
        "s": 1.25,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "shape",
    "sub": "rect",
    "x": 6.75,
    "y": 73.333,
    "w": 86.252,
    "h": 0.267,
    "fill": "#D0CABA",
    "bw": 0,
    "bc": null,
    "rx": 0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 76.0,
    "w": 45.001,
    "h": 6.667,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Obrigado.",
        "en": "Obrigado.",
        "s": 2.5,
        "b": true,
        "c": "#110E09",
        "f": "head"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 6.75,
    "y": 86.933,
    "w": 9.75,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "left",
      "runs": [
       {
        "pt": "Apoio:",
        "en": "Apoio:",
        "s": 1.563,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "img",
    "x": 15.0,
    "y": 85.333,
    "w": 7.014,
    "h": 6.4,
    "src": "/deck/slides/s30_5.webp"
   },
   {
    "kind": "img",
    "x": 26.251,
    "y": 86.267,
    "w": 9.215,
    "h": 4.933,
    "src": "/deck/slides/s30_6.webp"
   },
   {
    "kind": "text",
    "x": 56.251,
    "y": 86.933,
    "w": 36.751,
    "h": 5.333,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "Cristhian Kapelinski  ·  Orientador: Diego Kreutz",
        "en": "Cristhian Kapelinski  ·  Orientador: Diego Kreutz",
        "s": 1.458,
        "b": true,
        "c": "#564E42",
        "f": "sans"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   },
   {
    "kind": "text",
    "x": 93.377,
    "y": 93.333,
    "w": 5.25,
    "h": 4.0,
    "anchor": "start",
    "paras": [
     {
      "a": "right",
      "runs": [
       {
        "pt": "30",
        "en": "30",
        "s": 1.25,
        "b": false,
        "c": "#564E42",
        "f": "mono"
       }
      ]
     }
    ],
    "ml": 0.0,
    "mt": 0.0
   }
  ]
 }
];
