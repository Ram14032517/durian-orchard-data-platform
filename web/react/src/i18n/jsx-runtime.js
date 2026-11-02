import {jsx as nativeJsx,jsxs as nativeJsxs,Fragment} from 'react/jsx-runtime';
import {props} from '../../../i18n/english.js';
export {Fragment};
export const jsx=(type,input,key)=>nativeJsx(type,props(type,input),key);
export const jsxs=(type,input,key)=>nativeJsxs(type,props(type,input),key);
