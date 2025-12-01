Manipulate[
    DensityPlot[
        Sin[a x] Cos[b y], {x,0,10 Pi}, {y,0,5 Pi}
    ],
    {{a,1}, 0.5, 2, 0.05},
    {{b,1}, 0.5, 2, 0.05}
]
