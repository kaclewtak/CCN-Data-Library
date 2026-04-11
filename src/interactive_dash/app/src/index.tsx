import React, { useCallback, useContext, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { observer } from "mobx-react-lite";
import { reaction } from "mobx"
import { GraphicWalker, PureRenderer, GraphicRenderer, TableWalker } from '@kanaries/graphic-walker'
import type { VizSpecStore } from '@kanaries/graphic-walker/store/visualSpecStore'
import type { IGWHandler, IViewField, ISegmentKey, IDarkMode, IChatMessage, IRow } from '@kanaries/graphic-walker/interfaces';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib"
import { createRender, useModel } from "@anywidget/react";

import Options from './components/options';
import { IAppProps } from './interfaces';

import { loadDataSource, postDataService, finishDataService, getDatasFromKernelBySql, getDatasFromKernelByPayload } from './dataSource';

import commonStore from "./store/common";
import { initJupyterCommunication, initHttpCommunication, streamlitComponentCallback, initAnywidgetCommunication } from "./utils/communication";
import communicationStore from "./store/communication"
import { setConfig } from './utils/userConfig';
import CodeExportModal from './components/codeExportModal';
import type { IPreviewProps, IChartPreviewProps } from './components/preview';
import { Preview, ChartPreview } from './components/preview';
import UploadSpecModal from "./components/uploadSpecModal"
import UploadChartModal from './components/uploadChartModal';
import InitModal from './components/initModal';
import { getCcnFormulaTool } from './tools/ccnFormulaTool';
import { getSaveTool } from './tools/saveTool';
import { getExportTool } from './tools/exportTool';
import { getExportDataframeTool } from './tools/exportDataframe';
import { getRuncellTool } from './tools/runcellTool';
import { formatExportedChartDatas } from "./utils/save";
import { tracker } from "@/utils/tracker";
import Notification from "./notify"
import initDslParser from "@kanaries/gw-dsl-parser";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    ToggleGroup,
    ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { SunIcon, MoonIcon, DesktopIcon, ChevronLeftIcon, ChevronRightIcon } from "@radix-ui/react-icons"

// @ts-ignore
import style from './index.css?inline'
import { currentMediaTheme } from './utils/theme';
import { AppContext, darkModeContext } from './store/context';
import FormatSpec from './utils/formatSpec';
import { getOpenDesktopTool } from './tools/openDesktop';
import RuncellBanner from './components/runcellBanner';
import { CcnSpreadsheetPanel, useCcnSpreadsheetState } from '@/features/ccnSpreadsheet'

// ---- CCN ADDITION START: default config type ----
import type { IDefaultConfig } from '@kanaries/graphic-walker/interfaces';
// CCN SOFT-DISABLED: CoordSystemToggle moved from standalone JSX into
// the toolbar `extra` array as two toggle items.  The component file is
// kept for reference but no longer imported here.
// import CoordSystemToggle from './components/ccn/CoordSystemToggle';
import { GlobeAltIcon } from '@heroicons/react/24/outline';
// ---- CCN ADDITION END ----


const initChart = async (gwRef: React.MutableRefObject<IGWHandler | null>, total: number, props: IAppProps) => {
    if (props.needInitChart && props.env === "jupyter_widgets" && total !== 0) {
        commonStore.setInitModalOpen(true);
        commonStore.setInitModalInfo({
            title: "Recover Charts",
            curIndex: 0,
            total: total,
        });
        for await (const chart of gwRef.current?.exportChartList("data-url")!) {
            await communicationStore.comm?.sendMsg("save_chart", await formatExportedChartDatas(chart.data));
            commonStore.setInitModalInfo({
                title: "Recover Charts",
                curIndex: chart.index + 1,
                total: chart.total,
            });
        }
    }
    commonStore.setInitModalOpen(false);
}

const getComputationCallback = (props: IAppProps) => {
    if (props.useKernelCalc && props.parseDslType === "client") {
        return getDatasFromKernelBySql(props.fieldMetas);
    }
    if (props.useKernelCalc && props.parseDslType === "server") {
        return getDatasFromKernelByPayload;
    }
}

// ---- CCN ADDITION START: split CCN-only config from GraphicWalker props ----
const splitExtraConfig = (extraConfig?: IAppProps['extraConfig']) => {
    const { ccnSpreadsheet, ccnSharedDatasetBridge, ...graphicWalkerExtraConfig } = extraConfig ?? {};

    return {
        ccnSpreadsheet,
        ccnSharedDatasetBridge,
        graphicWalkerExtraConfig,
    };
};
// ---- CCN ADDITION END ----

const MainApp = observer((props: {children: React.ReactNode, darkMode: "dark" | "light" | "media", hideToolBar?: boolean, gid?: string, sendMessage?: boolean}) => {
    const [portal, setPortal] = useState<HTMLDivElement | null>(null);
    const [selectedDarkMode, setSelectedDarkMode] = useState(props.darkMode);
    const [darkMode, setDarkMode] = useState(currentMediaTheme(props.darkMode));

    const sendAppearanceMessageToParent = useCallback((appearance: IDarkMode) => {
        if (!props.sendMessage) return;
        window.parent.postMessage({
            action: "changeAppearance",
            gid: props.gid,
            appearance: appearance
        }, "*");
    }, [props.gid, props.sendMessage]);

    useEffect(() => {
        if (selectedDarkMode === "media") {
            setDarkMode(currentMediaTheme(selectedDarkMode));
            sendAppearanceMessageToParent(currentMediaTheme(selectedDarkMode));
            const media = window.matchMedia('(prefers-color-scheme: dark)');
            const listener = (e: MediaQueryListEvent) => {
                setDarkMode(e.matches ? "dark" : "light");
            }
            media.addEventListener("change", listener);
            return () => media.removeEventListener("change", listener);
        } else {
            sendAppearanceMessageToParent(selectedDarkMode);
            setDarkMode(selectedDarkMode);
        }
    }, [selectedDarkMode])

    return (
        <AppContext
            portalContainerContext={portal}
            darkModeContext={darkMode}
        >
            <div className={`${darkMode === "dark" ? "dark": ""} bg-background text-foreground`}>
                <div className="p-2">
                    <style>{style}</style>
                    <div className='overflow-y-auto'>
                        { props.children }
                    </div>
                    {!props.hideToolBar && (
                        <div className="flex w-full mt-1 p-1 overflow-hidden border-t border-border">
                            <ToggleGroup
                                type="single"
                                value={selectedDarkMode}
                                onValueChange={(value) => {value && setSelectedDarkMode(value as IDarkMode)}}
                            >
                                <ToggleGroupItem value="dark">
                                    <MoonIcon className="h-4 w-4" />
                                </ToggleGroupItem>
                                <ToggleGroupItem value="light">
                                    <SunIcon className="h-4 w-4" />
                                </ToggleGroupItem>
                                <ToggleGroupItem value="media">
                                    <DesktopIcon className="h-4 w-4" />
                                </ToggleGroupItem>
                            </ToggleGroup>
                        </div>
                    )}
                    <InitModal />
                    <div ref={setPortal}></div>
                </div>
            </div>
        </AppContext>
    )
})

const ExploreApp: React.FC<IAppProps & {initChartFlag: boolean}> = (props) => {
    const gwRef = React.useRef<IGWHandler|null>(null);
    const { userConfig } = props;
    const appearance = useContext(darkModeContext);
    const [exportOpen, setExportOpen] = useState(false);
    const [mode, setMode] = useState<string>("walker");
    const [visSpec, setVisSpec] = useState(props.visSpec);
    const [hideModeOption, _] = useState(true);
    const [isChanged, setIsChanged] = useState(false);
    // ---- CCN ADDITION START: track coord system for toolbar toggle reactivity ----
    const [coordSystem, setCoordSystem] = useState<string>('generic');
    // ---- CCN ADDITION END ----
    const storeRef = React.useRef<VizSpecStore|null>(null);
    const disposerRef = React.useRef<(() => void) | undefined>(undefined);
    const { ccnSpreadsheet, ccnSharedDatasetBridge, graphicWalkerExtraConfig } = React.useMemo(
        () => splitExtraConfig(props.extraConfig),
        [props.extraConfig],
    );
    const spreadsheetEnabled = Boolean(ccnSpreadsheet?.enabled && !props.useKernelCalc);
    const spreadsheetState = useCcnSpreadsheetState({
        enabled: spreadsheetEnabled,
        config: ccnSpreadsheet,
        bridgeConfig: ccnSharedDatasetBridge,
        initialRows: props.dataSource,
        initialFields: props.rawFields,
    });
    const activeDataSource = spreadsheetEnabled ? spreadsheetState.graphRows : props.dataSource;
    const activeFields = spreadsheetEnabled ? spreadsheetState.graphFields : props.rawFields;
    const walkerDatasetKey = spreadsheetEnabled
        ? `ccn-spreadsheet-${spreadsheetState.visualizationDatasetFingerprint}`
        : 'ccn-static-dataset';
    const previousWalkerDatasetKeyRef = React.useRef<string | null>(null);
    const storeRefProxied = React.useMemo(
        () =>
            new Proxy(storeRef, {
                set(target, prop, value) {
                    if (prop === "current") {
                        if (value) {
                            disposerRef.current?.();
                            const store = value as VizSpecStore;
                            disposerRef.current = reaction(
                                () => store.currentVis,
                                () => {
                                    setIsChanged((value as VizSpecStore).canUndo);
                                    // ---- CCN ADDITION START: sync coord system to React state ----
                                    setCoordSystem(store.currentVis?.config?.coordSystem ?? 'generic');
                                    // ---- CCN ADDITION END ----
                                    streamlitComponentCallback({
                                        event: "spec_change",
                                        data: store.exportCode()
                                    });
                                },
                            );
                        }
                    }
                    return Reflect.set(target, prop, value);
                },
            }),
        []
    );

    commonStore.setVersion(props.version!);

    useEffect(() => {
        commonStore.setShowCloudTool(props.showCloudTool);
        tracker.setUserId(props.hashcode ?? "");
        if (userConfig) {
            setConfig(userConfig);
            tracker.setOpen(userConfig.privacy === "events");
        };
    }, []);

    useEffect(() => {
        if (props.initChartFlag) {
            setTimeout(() => { initChart(gwRef, visSpec.length, props) }, 0);
        }
    }, [props.initChartFlag]);

    useEffect(() => {
        setTimeout(() => {
            storeRef.current?.setSegmentKey(props.defaultTab as ISegmentKey);
        }, 0);
    }, [mode]);

    useEffect(() => {
        if (!spreadsheetEnabled) {
            previousWalkerDatasetKeyRef.current = walkerDatasetKey;
            return;
        }

        if (previousWalkerDatasetKeyRef.current == null) {
            previousWalkerDatasetKeyRef.current = walkerDatasetKey;
            return;
        }

        if (previousWalkerDatasetKeyRef.current !== walkerDatasetKey) {
            previousWalkerDatasetKeyRef.current = walkerDatasetKey;
            setVisSpec([]);
        }
    }, [spreadsheetEnabled, walkerDatasetKey]);

    const runcellTool = getRuncellTool();
    const exportTool = getExportTool(setExportOpen);
    const openInDesktopTool = getOpenDesktopTool(props, storeRef);
    const ccnFormulaTool = getCcnFormulaTool(storeRef);

    const tools = [runcellTool, exportTool, openInDesktopTool];
    if (props.env && ["jupyter_widgets", "streamlit", "gradio", "marimo", "anywidget", "web_server"].indexOf(props.env) !== -1 && props.useSaveTool) {
        const saveTool = getSaveTool(props, gwRef, storeRef, isChanged, setIsChanged);
        tools.push(saveTool);
    }
    if (props.isExportDataFrame) {
        const exportDataFrameTool = getExportDataframeTool(props, storeRef);
        tools.push(exportDataFrameTool);
    }

    const toolbarConfig: any = {
        // ---- CCN ADDITION START: hide built-in coord_system dropdown ----
        // The built-in coord_system dropdown is excluded because our
        // two toggle items (ccn_coord_generic / ccn_coord_geographic)
        // render both modes as always-visible icons in the toolbar.
        // To restore the dropdown, remove "coord_system" from exclude
        // and remove the two CCN coord tools from the extra array.
        exclude: ["export_code", "coord_system"],
        // ---- CCN ADDITION END ----
        extra: [
            // ---- CCN ADDITION START: coord system toolbar toggles ----
            // These behave like radio buttons: clicking the inactive one
            // switches modes; clicking the already-active one is a no-op.
            // Both the MobX store AND the React state are updated directly
            // to avoid timing issues with the MobX reaction roundtrip.
            // Cartesian / crosshair icon  (matches graphic-walker built-in)
            {
                key: 'ccn_coord_generic',
                label: 'Cartesian',
                icon: (iconProps?: any) => (
                    <svg stroke="currentColor" fill="none" strokeWidth="1.5"
                         xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
                         aria-hidden="true" {...iconProps}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2 12h20M12 2v20" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 7h2M12 16h2M7 12v-2M16 12v-2" />
                    </svg>
                ),
                checked: coordSystem === 'generic',
                onChange: (checked: boolean) => {
                    if (checked) {
                        storeRef.current?.setCoordSystem('generic');
                        setCoordSystem('generic');
                    }
                },
            },
            // Geographic / globe icon
            {
                key: 'ccn_coord_geographic',
                label: 'Geographic',
                icon: (iconProps?: any) => <GlobeAltIcon {...iconProps} />,
                checked: coordSystem === 'geographic',
                onChange: (checked: boolean) => {
                    if (checked) {
                        storeRef.current?.setCoordSystem('geographic');
                        setCoordSystem('geographic');
                    }
                },
            },
            // ---- CCN ADDITION END ----
            '-',
            ...tools,
            '-',
            ccnFormulaTool,
        ],
    }

    const enhanceAPI = React.useMemo(() => {
        if (props.showCloudTool) {
            const features: Record<string, any> = {};
            if (props.enableAskViz) {
                features["askviz"] = async (metas: IViewField[], query: string) => {
                    const resp = await communicationStore.comm?.sendMsg("get_spec_by_text", { metas, query });
                    return resp?.data.data;
                };
            }
            if (props.enableVlChat) {
                features["vlChat"] = async (metas: IViewField[], chats: IChatMessage[]) => {
                    const resp = await communicationStore.comm?.sendMsg("get_chart_by_chats", { metas, chats });
                    return resp?.data.data;
                };
            }
            if (Object.keys(features).length > 0) {
                return { features };
            }
        }
        return undefined;
    }, [props.showCloudTool, props.enableAskViz, props.enableVlChat]);

    const computationCallback = React.useMemo(() => getComputationCallback(props), []);

    // ---- CCN ADDITION START: custom default configuration ----
    // Default layout: 600×600 fixed.  Aggregation: off.
    // Allows future Python-side overrides via props.extraConfig.defaultConfig.
    const ccnDefaultConfig: IDefaultConfig = {
        config: {
            timezoneDisplayOffset: 0,
            defaultAggregated: false,                    // CCN: aggregation off by default
            ...(graphicWalkerExtraConfig.defaultConfig?.config ?? {}),
        },
        layout: {
            size: { mode: 'fixed', width: 600, height: 600 }, // CCN: 600×600 fixed layout
            ...(graphicWalkerExtraConfig.defaultConfig?.layout ?? {}),
        },
    };
    // ---- CCN ADDITION END ----

    const modeChange = (value: string) => {
        if (mode === "walker") {
            setVisSpec(storeRef.current?.exportCode());
        }
        setMode(value);
    }

    const walkerView = (
        <GraphicWalker
            key={walkerDatasetKey}
            {...graphicWalkerExtraConfig}
            appearance={appearance}
            vizThemeConfig={props.themeKey}
            fieldKeyGuard={props.fieldkeyGuard}
            fields={activeFields}
            keepAlive={walkerDatasetKey}
            storeRef={storeRefProxied}
            ref={gwRef}
            toolbar={toolbarConfig}
            enhanceAPI={enhanceAPI}
            chart={visSpec.length === 0 ? undefined : visSpec}
            experimentalFeatures={{ computedField: props.useKernelCalc }}
            {...(props.useKernelCalc ? { computation: computationCallback! } : { data: activeDataSource })}
            // ---- CCN SOFT-DISABLED START: original hardcoded defaultConfig ----
            // Replaced by ccnDefaultConfig which sets 600×600 fixed layout and
            // disables aggregation by default.  Restore this line and remove
            // ccnDefaultConfig above to revert to upstream behaviour.
            // defaultConfig={{ config: { timezoneDisplayOffset: 0 } }}
            // ---- CCN SOFT-DISABLED END ----
            defaultConfig={ccnDefaultConfig}
        />
    );
  
    return (
        <React.StrictMode>
            <Notification />
            <UploadSpecModal storeRef={storeRef} setGwIsChanged={setIsChanged} />
            <UploadChartModal gwRef={gwRef} storeRef={storeRef} dark={useContext(darkModeContext)} />
            <CodeExportModal open={exportOpen} setOpen={setExportOpen} globalStore={storeRef} sourceCode={props["sourceInvokeCode"] || ""} />
            {/* ---- CCN SOFT-DISABLED START: standalone coord toggle ----
              * Moved into the toolbar `extra` array as two toggle items so the
              * icons appear alongside the other toolbar options instead of at
              * the top level.  See toolbarConfig above.
              * <CoordSystemToggle storeRef={storeRefProxied} />
              * ---- CCN SOFT-DISABLED END ---- */}
            {
                !hideModeOption &&
                <Select onValueChange={modeChange} defaultValue='walker' >
                    <SelectTrigger className="w-[140px] h-[30px] mb-[20px] text-xs">
                        <span className='text-muted-foreground'>Mode: </span>
                        <SelectValue className='' placeholder="Mode" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="walker">Walker</SelectItem>
                        <SelectItem value="renderer">Renderer</SelectItem>
                    </SelectContent>
                </Select>
            }
            {
                mode === "walker" ? 
                (spreadsheetEnabled ?
                    // ---- CCN ADDITION START: in-frame spreadsheet + walker split layout ----
                    <div className="ccn-explore-layout">
                        <CcnSpreadsheetPanel state={spreadsheetState} />
                        <div className="ccn-graphicwalker-panel">
                            {walkerView}
                        </div>
                    </div>
                    // ---- CCN ADDITION END ----
                    : walkerView) :
                <GraphicRendererApp
                    {...props}
                    dataSource={props.dataSource}
                    visSpec={visSpec}
                />
            }
            <Options {...props} />
        </React.StrictMode>
    );
}

const PureRednererApp: React.FC<IAppProps> = observer((props) => {
    const computationCallback = getComputationCallback(props);
    const appearance = useContext(darkModeContext);
    const spec = props.visSpec[0];
    const [expand, setExpand] = useState(false);
    const { graphicWalkerExtraConfig } = React.useMemo(
        () => splitExtraConfig(props.extraConfig),
        [props.extraConfig],
    );

    return (
        <React.StrictMode>
            <div className='flex'>
                {
                    !expand && (<PureRenderer
                        {...graphicWalkerExtraConfig}
                        appearance={appearance}
                        vizThemeConfig={props.themeKey}
                        name={spec.name}
                        visualConfig={spec.config}
                        visualLayout={spec.layout}
                        visualState={spec.encodings}
                        type='remote'
                        computation={computationCallback!}
                    />)
                }
                {
                    expand && commonStore.isStreamlitComponent && (
                        <div style={{minWidth: "96%"}}>
                            <GraphicWalker
                                {...graphicWalkerExtraConfig}
                                appearance={appearance}
                                vizThemeConfig={props.themeKey}
                                fieldKeyGuard={props.fieldkeyGuard}
                                fields={props.rawFields}
                                chart={props.visSpec}
                                experimentalFeatures={{ computedField: props.useKernelCalc }}
                                {...(props.useKernelCalc ? { computation: computationCallback! } : { data: props.dataSource })}
                                // ---- CCN SOFT-DISABLED START: original hardcoded defaultConfig ----
                                // defaultConfig={{ config: { timezoneDisplayOffset: 0 } }}
                                // ---- CCN SOFT-DISABLED END ----
                                defaultConfig={{
                                    config: { timezoneDisplayOffset: 0, defaultAggregated: false },
                                    layout: { size: { mode: 'fixed', width: 600, height: 600 } },
                                }}
                            />
                        </div>
                    )
                }
                { commonStore.isStreamlitComponent && expand && ( <ChevronLeftIcon className='h-6 w-6 cursor-pointer border border-black-600 rounded-full'onClick={() => setExpand(false)}></ChevronLeftIcon> )}
                { commonStore.isStreamlitComponent && !expand && ( <ChevronRightIcon className='h-6 w-6 cursor-pointer border border-black-600 rounded-full'onClick={() => setExpand(true)}></ChevronRightIcon> )}
            </div>
        </React.StrictMode>
    )
});

const initOnJupyter = async(props: IAppProps) => {
    const comm = initJupyterCommunication(props.id);
    comm.registerEndpoint("postData", postDataService);
    comm.registerEndpoint("finishData", finishDataService);
    communicationStore.setComm(comm);
    if (props.needLoadLastSpec) {
        const visSpecResp = await comm.sendMsg("get_latest_vis_spec", {});
        props.visSpec = FormatSpec(visSpecResp["data"]["visSpec"], props.rawFields);
    }
    if (props.needLoadDatas) {
        comm.sendMsgAsync("request_data", {}, null);
    }
    await initDslParser();
}

const initOnHttpCommunication = async(props: IAppProps) => {
    const comm = await initHttpCommunication(props.id, props.communicationUrl);
    communicationStore.setComm(comm);
    if ((props.gwMode === "explore" || props.gwMode === "filter_renderer") && props.needLoadLastSpec) {
        const visSpecResp = await comm.sendMsg("get_latest_vis_spec", {});
        props.visSpec = visSpecResp["data"]["visSpec"];
    }
    await initDslParser();
}

const initOnAnywidgetCommunication = async(props: IAppProps, model: import("@anywidget/types").AnyModel) => {
    const comm = await initAnywidgetCommunication(props.id, model);
    communicationStore.setComm(comm);
    if ((props.gwMode === "explore" || props.gwMode === "filter_renderer") && props.needLoadLastSpec) {
        const visSpecResp = await comm.sendMsg("get_latest_vis_spec", {});
        props.visSpec = visSpecResp["data"]["visSpec"];
    }
    await initDslParser();
}

const defaultInit = async(props: IAppProps) => {}

function GWalkerComponent(props: IAppProps) {
    const [initChartFlag, setInitChartFlag] = useState(false);
    const [dataSource, setDataSource] = useState<IRow[]>(props.dataSource);

    useEffect(() => {
        if (props.needLoadDatas) {
            loadDataSource(props.dataSourceProps).then((data) => {
                setDataSource(data);
                setInitChartFlag(true);
                commonStore.setInitModalOpen(false);
            })
        } else {
            setInitChartFlag(true);
        }
    }, []);

    if (props.gwMode === "explore") {
        return (
            <React.StrictMode>
                <RuncellBanner env={props.env} />
                <ExploreApp {...props} dataSource={dataSource} initChartFlag={initChartFlag} />
            </React.StrictMode>
        )
    }

    return (
        <React.StrictMode>
            <RuncellBanner env={props.env} />
            { props.gwMode === "renderer" && <PureRednererApp {...props} dataSource={dataSource}  /> }
            { props.gwMode === "filter_renderer" && <GraphicRendererApp {...props} dataSource={dataSource} /> }
            { props.gwMode === "table" && <TableWalkerApp {...props} dataSource={dataSource} /> }
        </React.StrictMode>
    )
}

function GWalker(props: IAppProps, id: string) {
    props.visSpec = FormatSpec(props.visSpec, props.rawFields);
    let preRender = defaultInit;
    switch(props.env) {
        case "jupyter_widgets":
            preRender = initOnJupyter;
            break;
        case "streamlit":
            preRender = initOnHttpCommunication;
            break;
        case "gradio":
            preRender = initOnHttpCommunication;
            break;
        case "web_server":
            preRender = initOnHttpCommunication;
            break;
        default:
            preRender = defaultInit;
    }

    preRender(props).then(() => {
        const container = document.getElementById(id);
        if (container) {
            createRoot(container).render(
                <MainApp darkMode={props.dark} gid={props.id} sendMessage={props.env?.startsWith("jupyter")}>
                    <GWalkerComponent {...props} />
                </MainApp>
            );
        }
    })
}

function PreviewApp(props: IPreviewProps, containerId: string) {
    props.charts = FormatSpec(props.charts.map(chart => chart.visSpec), [])
                    .map((visSpec, index) => { return {...props.charts[index], visSpec} });

    if (window.document.getElementById(`gwalker-${props.gid}`)) {
        window.document.getElementById(containerId)?.remove();
    }

    const container = document.getElementById(containerId);
    if (container) {
        createRoot(container).render(
            <MainApp darkMode={props.dark} hideToolBar>
                <Preview {...props} />
            </MainApp>
        );
    }
}

function ChartPreviewApp(props: IChartPreviewProps, id: string) {
    props.visSpec = FormatSpec([props.visSpec], [])[0];
    const container = document.getElementById(id);
    if (container) {
        createRoot(container).render(
            <MainApp darkMode={props.dark} hideToolBar>
                <ChartPreview {...props} />
            </MainApp>
        );
    }
}

function GraphicRendererApp(props: IAppProps) {
    const computationCallback = getComputationCallback(props);
    const containerSize = props["containerSize"] ?? [null, null];
    const globalProps = {
        rawFields: props.rawFields,
        containerStyle: {
            height: containerSize[1] ? `${containerSize[1]-200}px` : "700px",
            width: containerSize[0] ? `${containerSize[0]-20}px` : "60%"
        },
        themeKey:props.themeKey,
        dark: useContext(darkModeContext),
    }

    return (
        <React.StrictMode>
            <Tabs defaultValue="0" className="w-full">
                <div className="overflow-x-auto max-w-full">
                    <TabsList>
                        {props.visSpec.map((chart, index) => {
                            return <TabsTrigger key={index} value={index.toString()}>{chart.name}</TabsTrigger>
                        })}
                    </TabsList>
                </div>
                {props.visSpec.map((chart, index) => {
                    return <TabsContent key={index} value={index.toString()}>
                        {
                            props.useKernelCalc ? 
                            <GraphicRenderer
                                {...globalProps}
                                computation={computationCallback!}
                                chart={[chart]}
                            /> :
                            <GraphicRenderer
                                {...globalProps}
                                data={props.dataSource!}
                                chart={[chart]}
                            />
                        }
                    </TabsContent>
                })}
            </Tabs>
        </React.StrictMode>
    )
}

function TableWalkerApp(props: IAppProps) {
    const computationCallback = getComputationCallback(props);
    const globalProps = {
        rawFields: props.rawFields,
        themeKey: props.themeKey,
        dark: useContext(darkModeContext)
    }

    return (
        <React.StrictMode>
            {
                props.useKernelCalc ?
                <TableWalker
                    {...globalProps}
                    computation={computationCallback!}
                /> :
                <TableWalker
                    {...globalProps}
                    data={props.dataSource}
                />
            }
        </React.StrictMode>
    )
}


function SteamlitGWalkerApp(streamlitProps: any) {
    const props = streamlitProps.args as IAppProps;
    const [inited, setInited] = useState(false);
    const container = React.useRef<HTMLDivElement>(null);
    props.visSpec = FormatSpec(props.visSpec, props.rawFields);

    useEffect(() => {
        commonStore.setIsStreamlitComponent(true);
        initOnHttpCommunication(props).then(() => {
            setInited(true);
        })
    }, []);

    useEffect(() => {
        if (!container.current) return;
        const resizeObserver = new ResizeObserver(() => {
            Streamlit.setFrameHeight((container.current?.clientHeight  ?? 0) + 20);
        })
        resizeObserver.observe(container.current);
        return () => resizeObserver.disconnect();
    }, [inited]);

    return (
        <React.StrictMode>
            {inited && (
                <div ref={container}>
                    <MainApp darkMode={props.dark}>
                        <GWalkerComponent {...props} />
                    </MainApp>
                </div>
            )}
        </React.StrictMode>
    );
};

const StreamlitGWalker = () => {
    const StreamlitGWalkerComponent = withStreamlitConnection(SteamlitGWalkerApp);
    const container = document.getElementById("root");
    if (container) {
        createRoot(container).render(
            <React.StrictMode>
                <StreamlitGWalkerComponent />
            </React.StrictMode>
        );
    }
}

function AnywidgetGWalkerApp() {
    const [inited, setInited] = useState(false);
    const model = useModel();
    const props = JSON.parse(model.get("props")) as IAppProps;
    props.visSpec = FormatSpec(props.visSpec, props.rawFields);

    useEffect(() => {
        initOnAnywidgetCommunication(props, model).then(() => {
            setInited(true);
        })
    }, []);

    return (
        <React.StrictMode>
            {!inited && <div>Loading...</div>}
            {inited && (
                <MainApp darkMode={props.dark}>
                    <GWalkerComponent {...props} />
                </MainApp>
            )}
        </React.StrictMode>
    );
}


export default { GWalker, PreviewApp, ChartPreviewApp, StreamlitGWalker, render: createRender(AnywidgetGWalkerApp) }
